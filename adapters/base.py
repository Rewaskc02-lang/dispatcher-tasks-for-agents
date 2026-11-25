"""The agent adapter interface — the only place where the dispatcher knows anything about a particular agent.

The scheduler (``taskdispatch``) calls just these:

    start(task)        -> run id        start a new session with the task's brief
    resume(run, text)  -> run id        continue the same session (only if ``can_resume``; otherwise the scheduler starts a
                                        new run with a "continue" brief and the last report)
    status(run)        -> Outcome       running / done / limit / error, exit code, the session id
    report(run)        -> str           the run's final text
    limits()           -> dict | None   optional: {"<window>": {"used": %, "resets": unix time}} if the agent can tell

``ProcessAdapter`` implements the first four for agents that are a command-line program: it runs the program in the
background (``python3 dispatcher.py _run <run dir>``), with the brief on stdin, in the task's folder, and keeps its output
in the run folder. A concrete adapter then only says *which command* (``command``) and *how to read its output*
(``parse``). See ``adapters/_template.py`` and CONTRIBUTING.md.

Credentials: an adapter never reads, stores or passes on a password, token or key. The agent program uses the user's own
sign-in. For a worker with ``"auth": "subscription"`` the API-key variables listed in ``KEY_VARS`` are removed from the
child's environment (so a stray key does not silently bill an API account); with ``"auth": "api"`` the environment is passed
as it is and the agent reads its key itself.
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

DISPATCHER = Path(__file__).resolve().parent.parent / "dispatcher.py"
RUNNING, DONE, LIMIT, ERROR = "running", "done", "limit", "error"
LIMIT_WORDS = re.compile(r"usage limit|rate.?limit|limit reached|hit your limit|quota|resource.?exhausted|too many requests|"
                         r"\b429\b|out of (?:extra )?usage", re.I)


@dataclass
class Outcome:
    status: str                                 # running | done | limit | error
    exit_code: Optional[int] = None
    report: str = ""
    session: str = ""                           # the agent's session id, if it has one (for resume)
    windows: Dict[str, Dict[str, float]] = field(default_factory=dict)   # what the run's own output said about limits
    resets_at: float = 0.0                      # a hit limit resets at this time, if the agent said
    cost_usd: Optional[float] = None            # if the agent reports cost (API use)
    why: str = ""

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)


def spawn_detached(run_dir: Path) -> None:
    """Start ``dispatcher.py _run <run dir>`` in the background, outside this process's session."""
    subprocess.Popen([sys.executable, str(DISPATCHER), "_run", str(run_dir)], stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True)


class Adapter:
    """The interface. Subclass ``ProcessAdapter`` for a command-line agent."""
    name = "base"
    can_resume = False
    reported_windows: Optional[Tuple[str, str]] = None      # (short, long) names in limits(), when the agent reports them

    def __init__(self, worker: Dict[str, Any], runs: Path, spawn: Optional[Callable[[Path], None]] = None):
        self.worker = worker
        self.runs = Path(runs)
        self.spawn = spawn or spawn_detached

    def new_session(self) -> str:
        """A session id the dispatcher chooses before the start, or '' if the agent assigns its own (read in parse)."""
        return ""

    def start(self, task: Dict[str, Any]) -> str:
        raise NotImplementedError

    def resume(self, run: str, text: str, task: Dict[str, Any]) -> str:
        raise NotImplementedError

    def status(self, run: str) -> Outcome:
        raise NotImplementedError

    def report(self, run: str) -> str:
        return self.status(run).report

    def limits(self) -> Optional[Dict[str, Dict[str, float]]]:
        return None


class ProcessAdapter(Adapter):
    """A command-line agent run in the background. Subclasses implement ``command`` and ``parse``."""
    binary = ""                                  # default program name; the worker's "bin" overrides it
    KEY_VARS: Tuple[str, ...] = ()

    # ---- what a concrete adapter provides
    def command(self, task: Dict[str, Any], *, resume: bool, text: str) -> Tuple[List[str], Optional[str]]:
        """(argv, stdin text or None) for a start (resume=False, text = the brief) or a resume (text = the follow-up)."""
        raise NotImplementedError

    def parse(self, out: str, err: str, code: int) -> Outcome:
        raise NotImplementedError

    # ---- helpers for subclasses
    def bin(self) -> List[str]:
        value = self.worker.get("bin") or self.binary
        return [str(x) for x in value] if isinstance(value, list) else [str(value)]

    def extra(self) -> List[str]:
        return [str(x) for x in self.worker.get("args") or []]

    def env(self) -> Dict[str, str]:
        env = dict(os.environ)
        if self.worker.get("auth", "subscription") != "api":
            for key in self.KEY_VARS:
                env.pop(key, None)
        return env

    # ---- the interface
    def _launch(self, task: Dict[str, Any], *, resume: bool, text: str) -> str:
        run = f"{task['id']}/{task['n']}"
        d = self.runs / run
        d.mkdir(parents=True, exist_ok=True)
        argv, stdin = self.command(task, resume=resume, text=text)
        (d / "prompt.md").write_text(text, encoding="utf-8")
        if stdin is not None:
            (d / "stdin.txt").write_text(stdin, encoding="utf-8")
        meta = {"argv": argv, "cwd": str(Path(task["cwd"]).expanduser()), "stdin": stdin is not None,
                "worker": self.worker["name"], "agent": self.name, "task": task["id"], "n": task["n"]}
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        self.spawn(d)
        return run

    def start(self, task: Dict[str, Any]) -> str:
        return self._launch(task, resume=False, text=task["brief"])

    def resume(self, run: str, text: str, task: Dict[str, Any]) -> str:
        return self._launch(task, resume=True, text=text)

    def status(self, run: str) -> Outcome:
        d = self.runs / run
        try:
            code = int((d / "exit").read_text().strip())
        except (OSError, ValueError):
            pid = _read_int(d / "pid")
            if pid and _alive(pid):
                return Outcome(RUNNING)
            if not (d / "pid").exists() and not (d / "started").exists():
                return Outcome(RUNNING, why="not started yet")
            return Outcome(ERROR, why="the run stopped without an exit code")
        out = _read(d / "out.txt")
        err = _read(d / "err.txt")
        return self.parse(out, err, code)

    def stop(self, run: str) -> None:
        pid = _read_int(self.runs / run / "pid")
        if pid:
            try:
                os.killpg(pid, signal.SIGTERM)
            except OSError:
                pass


def _read(path: Path, tail: int = 2_000_000) -> str:
    try:
        return path.read_bytes()[-tail:].decode("utf-8", "replace")
    except OSError:
        return ""


def _read_int(path: Path) -> int:
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return 0


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def json_lines(text: str) -> List[Dict[str, Any]]:
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict):
                out.append(obj)
    return out
