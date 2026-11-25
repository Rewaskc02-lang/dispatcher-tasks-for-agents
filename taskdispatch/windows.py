"""Usage windows — one idea for every agent.

A worker may have a *short* window (e.g. a few hours) and a *long* one (e.g. a week). For each window the dispatcher
needs two numbers: how much is used (0–100 %) and when it resets. They come from one of three places, per worker:

* ``"windows": "reported"`` — the agent's own output says so (the ``claude`` adapter reads them from the CLI's normal
  JSON output; see ``Adapter.limits``);
* ``"windows": [{"name": "short", "hours": 5}, {"name": "week", "hours": 168}]`` — you know your plan; the dispatcher
  counts its own runs: a window opens with the first task after the previous one closed, and each task uses its size
  (S/M/L/XL, a share of the short window; for longer windows multiplied by ``size_scale``);
* ``"budget_usd": {"amount": 5, "hours": 24}`` — for API keys: money instead of windows, counted from the cost the agent
  reports for each run (only agents that report cost);
* nothing — unknown: one task at a time, and after a run hits a limit the worker pauses until the reset the agent named,
  or for ``pause_after_limit_minutes``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

DEFAULT_RESERVE = 10.0          # % of the short window kept free (you may be using the same plan by hand)
DEFAULT_RESERVE_LONG = 3.0
DEFAULT_PAUSE_MINUTES = 60.0
WEEK_HOURS = 7 * 24


@dataclass
class Window:
    used: float                 # %
    resets: float               # unix time; 0 — unknown

    def fresh(self, at: float) -> "Window":
        """A window whose reset has passed is empty."""
        return Window(0.0, 0.0) if self.resets and self.resets <= at else self


@dataclass
class View:
    """What the dispatcher knows about one worker right now."""
    worker: str
    short: Optional[Window] = None
    long: Optional[Window] = None
    long_scale: float = 0.12            # share of the long window per 1 % of the short one
    paused_until: float = 0.0
    recent: float = 0.0                 # sizes (in % of a short window) this worker started in the last 7 days
    source: str = "unknown"             # reported | configured | budget | unknown
    notes: List[str] = field(default_factory=list)

    @property
    def load(self) -> Optional[float]:
        """How much of the long window is used — the measure for «who has the most weekly headroom»."""
        return self.long.used if self.long else None


def _accounted(turns: List[Dict[str, Any]], hours: float, scale: float, at: float) -> Window:
    """Own accounting of one configured window: it opens with the first run after the previous one closed."""
    span = hours * 3600
    start = 0.0
    used = 0.0
    for t in sorted(turns, key=lambda x: x["at"]):
        if not start or t["at"] >= start + span:
            start, used = t["at"], 0.0
        used += t["size"] * scale
    if not start or at >= start + span:
        return Window(0.0, 0.0)
    return Window(min(100.0, used), start + span)


def view(worker: Dict[str, Any], *, turns: List[Dict[str, Any]], cache: Dict[str, Any], reported_names=None,
         at: float) -> View:
    """turns — this worker's runs: {'at', 'size' (% of a short window), 'cost_usd'}; cache — limits.json for it."""
    v = View(worker["name"], paused_until=float(cache.get("paused_until") or 0))
    v.recent = sum(t["size"] for t in turns if t["at"] >= at - WEEK_HOURS * 3600)
    spec = worker.get("windows")
    budget = worker.get("budget_usd")
    if isinstance(budget, dict) and budget.get("amount"):
        hours = float(budget.get("hours") or 24)
        spent = [t for t in turns if t["at"] >= at - hours * 3600 and t.get("cost_usd")]
        used = 100.0 * sum(float(t["cost_usd"]) for t in spent) / float(budget["amount"])
        resets = min((t["at"] for t in spent), default=0.0) + hours * 3600 if spent else 0.0
        v.short = v.long = Window(min(100.0, used), resets)
        v.long_scale = 1.0
        v.source = "budget"
    elif spec == "reported":
        got = cache.get("windows") or {}
        short_name, long_name = reported_names or ("short", "long")
        if isinstance(got.get(short_name), dict):
            v.short = Window(float(got[short_name]["used"]), float(got[short_name].get("resets") or 0)).fresh(at)
        if isinstance(got.get(long_name), dict):
            v.long = Window(float(got[long_name]["used"]), float(got[long_name].get("resets") or 0)).fresh(at)
        v.long_scale = float(worker.get("long_size_scale") or 0.12)
        v.source = "reported" if (v.short or v.long) else "unknown"
        if not (v.short or v.long):
            v.notes.append("no limits reported yet")
    elif isinstance(spec, list) and spec:
        wins = sorted((w for w in spec if isinstance(w, dict) and w.get("hours")), key=lambda w: float(w["hours"]))
        if wins:
            first = wins[0]
            v.short = _accounted(turns, float(first["hours"]), float(first.get("size_scale") or 1.0), at)
            if len(wins) > 1:
                last = wins[-1]
                scale = float(last.get("size_scale") or float(first["hours"]) / float(last["hours"]))
                v.long = _accounted(turns, float(last["hours"]), scale, at)
                v.long_scale = scale
            v.source = "configured"
    return v


def fits(v: View, size: float, worker: Dict[str, Any], at: float) -> tuple:
    """(fits now?, why not). Unknown windows fit unless the worker is pausing after a limit."""
    if v.paused_until > at:
        return False, f"{v.worker}: paused after a usage limit until {_clock(v.paused_until, at)}"
    reserve = float(worker.get("reserve_percent", DEFAULT_RESERVE))
    if v.short:
        head = 100.0 - v.short.used - reserve
        if size > head:
            return False, (f"{v.worker}: short window has {head:.0f} % free after the {reserve:.0f} % reserve, the task needs "
                           f"~{size:.0f} % (resets {_clock(v.short.resets, at)})")
    if v.long:
        head = 100.0 - v.long.used - float(worker.get("reserve_long_percent", DEFAULT_RESERVE_LONG))
        if size * v.long_scale > head:
            return False, f"{v.worker}: long window has {head:.0f} % free, the task needs ~{size * v.long_scale:.1f} %"
    return True, ""


def ready_at(v: View, at: float) -> float:
    """When this worker's blocker should clear (0 — unknown)."""
    times = [t for t in (v.paused_until, v.short.resets if v.short else 0) if t and t > at]
    return min(times) if times else 0.0


def _clock(ts: float, at: float) -> str:
    if not ts:
        return "at an unknown time"
    d = ts - at
    if d <= 0:
        return "now"
    if d < 3600:
        return f"in {int(d // 60)} min"
    if d < 86400:
        return f"in {int(d // 3600)} h {int(d % 3600 // 60)} min"
    return f"in {d / 86400:.1f} days"


clock = _clock
