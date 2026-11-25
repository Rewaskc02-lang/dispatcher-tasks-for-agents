"""Claude Code (`claude`) — start, resume the same session, limits read from the CLI's own output.

* start:  ``claude -p --output-format stream-json --verbose --session-id <uuid> [--model M] [args…]`` with the brief on stdin
* resume: the same with ``--resume <uuid>`` and the follow-up on stdin
* report: the ``result`` event's text; cost: its ``total_cost_usd`` (reported for API-key use)
* limits: the CLI prints ``rate_limit_event`` lines in its normal stream-json output (with a subscription: the usage of
  its windows and their reset times). Every finished run updates them for free. ``limits()`` (the probe) is one ordinary,
  tiny ``claude -p`` request — Haiku, no tools, no session saved, a one-word answer — made only when the cached numbers
  are older than ``probe_minutes`` (default 10) and a task is waiting; it counts against your plan like any request.
  ``"probe_minutes": 0`` turns it off (then only the runs' own output is used).
* a run stopped by a limit: a ``rate_limit_event`` with status ``rejected``, or an error result that says so.

The adapter never touches your sign-in: it starts the unmodified ``claude`` you are already signed in to.
"""
from __future__ import annotations

import subprocess
import uuid
from typing import Any, Dict, List, Optional, Tuple

from adapters.base import DONE, ERROR, LIMIT, LIMIT_WORDS, Outcome, ProcessAdapter, json_lines

PROBE_ARGS = ["-p", "--model", "haiku", "--tools", "", "--no-session-persistence", "--strict-mcp-config",
              "--output-format", "stream-json", "--verbose", "--system-prompt", "Reply with one word."]


def read_windows(events: List[Dict[str, Any]]) -> Tuple[Dict[str, Dict[str, float]], float, bool]:
    """(windows, resets_at of a rejected window, rejected?) from the stream's rate_limit_event lines. Several events may
    come in one run, each with some of the windows — later ones win."""
    windows: Dict[str, Dict[str, float]] = {}
    resets, rejected = 0.0, False
    for ev in events:
        if ev.get("type") != "rate_limit_event":
            continue
        info = ev.get("rate_limit_info") or {}
        if info.get("status") == "rejected":
            rejected = True
            resets = max(resets, float(info.get("resetsAt") or 0))
        for name, w in (info.get("unifiedWindows") or {}).items():
            if not isinstance(w, dict):
                continue
            if w.get("status") == "rejected":
                rejected = True
                resets = max(resets, float(w.get("resetsAt") or 0))
            if w.get("utilization") is not None:
                windows[name] = {"used": round(100 * float(w["utilization"]), 1), "resets": float(w.get("resetsAt") or 0)}
    # the long window: the fullest of the weekly ones (seven_day, seven_day_opus, …)
    weekly = [w for n, w in windows.items() if n.startswith("seven_day")]
    if weekly:
        windows["long"] = max(weekly, key=lambda w: w["used"])
    if "five_hour" in windows:
        windows["short"] = windows["five_hour"]
    return windows, resets, rejected


class ClaudeAdapter(ProcessAdapter):
    name = "claude"
    binary = "claude"
    can_resume = True
    reported_windows = ("short", "long")
    KEY_VARS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")

    def new_session(self) -> str:
        return str(uuid.uuid4())

    def command(self, task: Dict[str, Any], *, resume: bool, text: str) -> Tuple[List[str], Optional[str]]:
        argv = self.bin() + ["-p", "--output-format", "stream-json", "--verbose"]
        argv += ["--resume", task["session"]] if resume else ["--session-id", task["session"]]
        if self.worker.get("model"):
            argv += ["--model", str(self.worker["model"])]
        return argv + self.extra(), text

    def parse(self, out: str, err: str, code: int) -> Outcome:
        events = json_lines(out)
        windows, resets, rejected = read_windows(events)
        result = next((e for e in reversed(events) if e.get("type") == "result"), None) or {}
        report = str(result.get("result") or "")
        session = str(result.get("session_id") or next((e.get("session_id") for e in events if e.get("session_id")), "") or "")
        cost = result.get("total_cost_usd")
        o = Outcome(DONE, code, report, session, windows, resets, float(cost) if isinstance(cost, (int, float)) else None)
        if rejected or (result.get("is_error") and LIMIT_WORDS.search(report)) or (not result and LIMIT_WORDS.search(err)):
            o.status, o.why = LIMIT, "usage limit reached"
        elif code != 0 or result.get("is_error") or not result:
            o.status = ERROR
            last_err = (err.strip().splitlines() or [""])[-1]
            o.why = (report or last_err or f"exit code {code}")[:300]
        return o

    def limits(self) -> Optional[Dict[str, Dict[str, float]]]:
        try:
            done = subprocess.run(self.bin() + PROBE_ARGS, input="ok", capture_output=True, text=True, timeout=120,
                                  env=self.env())
        except (OSError, subprocess.SubprocessError):
            return None
        windows, _, _ = read_windows(json_lines(done.stdout))
        return windows or None
