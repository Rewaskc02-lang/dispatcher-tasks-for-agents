"""The dispatcher's home folder: config, queue state, run folders, events, caches.

Home is ``$DISPATCHER_HOME`` or ``~/.config/dispatcher-tasks``. Everything is plain JSON; every read-modify-write of the
state happens under one file lock, and files are replaced atomically so a reader never sees a half-written file.
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

SIZES = {"S": 3.0, "M": 10.0, "L": 25.0, "XL": 50.0}       # % of a worker's short usage window (calibrated in sizes.json)


def default_home() -> Path:
    env = os.environ.get("DISPATCHER_HOME")
    return Path(env).expanduser() if env else Path.home() / ".config" / "dispatcher-tasks"


def now() -> float:
    return time.time()


def iso(ts: Optional[float] = None) -> str:
    return datetime.fromtimestamp(now() if ts is None else ts, timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="." + path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


class Home:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else default_home()

    # ---- files
    @property
    def config_path(self) -> Path:
        return self.path / "config.json"

    @property
    def state_path(self) -> Path:
        return self.path / "queue.json"

    @property
    def events_path(self) -> Path:
        return self.path / "events.jsonl"

    @property
    def limits_path(self) -> Path:
        return self.path / "limits.json"

    @property
    def sizes_path(self) -> Path:
        return self.path / "sizes.json"

    def run_dir(self, task_id: str, n: int) -> Path:
        return self.path / "runs" / task_id / str(n)

    # ---- config
    def config(self) -> Dict[str, Any]:
        data = read_json(self.config_path, None)
        if not isinstance(data, dict):
            raise SystemExit(f"no config at {self.config_path} — run: python3 dispatcher.py init")
        data.setdefault("workers", [])
        return data

    def workers(self) -> List[Dict[str, Any]]:
        """The enabled workers. One per agent: the dispatcher schedules your work on your agents; it does not spread work
        over several accounts of one agent (that would be a way around a plan's limits, which it does not do)."""
        out = [w for w in self.config()["workers"] if w.get("enabled", True)]
        agents: Dict[str, str] = {}
        for w in out:
            if not w.get("name"):
                raise SystemExit(f"{self.config_path}: a worker without a name")
            agent = str(w.get("agent") or w["name"])
            if agent in agents:
                raise SystemExit(f"{self.config_path}: workers {agents[agent]!r} and {w['name']!r} both use {agent!r} — one "
                                 "worker per agent (the dispatcher does not spread work over several accounts)")
            agents[agent] = w["name"]
        return out

    # ---- sizes
    def sizes(self) -> Dict[str, float]:
        learned = read_json(self.sizes_path, {})
        return {**SIZES, **{k: float(v) for k, v in learned.items() if k in SIZES and isinstance(v, (int, float))}}

    # ---- state
    @contextlib.contextmanager
    def locked(self) -> Iterator[None]:
        self.path.mkdir(parents=True, exist_ok=True)
        with open(self.path / "queue.lock", "a") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    def state(self) -> Dict[str, Any]:
        data = read_json(self.state_path, {})
        data = data if isinstance(data, dict) else {}
        data.setdefault("items", [])        # waiting tasks
        data.setdefault("tasks", {})        # started tasks: id → {worker, session, turns, ...}
        data.setdefault("moved", {})        # queue id → task id it went into (a --with that continued another session)
        return data

    @contextlib.contextmanager
    def changing(self) -> Iterator[Dict[str, Any]]:
        with self.locked():
            data = self.state()
            yield data
            write_json(self.state_path, data)

    # ---- limits cache (per worker: windows the agent reported, when, paused_until after a limit hit)
    def limits_cache(self) -> Dict[str, Any]:
        data = read_json(self.limits_path, {})
        return data if isinstance(data, dict) else {}

    def update_limits(self, worker: str, **fields: Any) -> None:
        """limits.json has its own lock: it is written while the state lock is held (a run's end, a tick)."""
        self.path.mkdir(parents=True, exist_ok=True)
        with open(self.path / "limits.lock", "a") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                data = self.limits_cache()
                data[worker] = {**(data.get(worker) or {}), **fields}
                write_json(self.limits_path, data)
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    # ---- events
    def event(self, kind: str, task: str = "", why: str = "", **more: Any) -> Dict[str, Any]:
        row = {"at": iso(), "event": kind, "task": task, "why": why, **more}
        self.path.mkdir(parents=True, exist_ok=True)
        with open(self.events_path, "a", encoding="utf-8") as fh:     # one line, one write
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    def events(self, limit: int = 0) -> List[Dict[str, Any]]:
        try:
            lines = self.events_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        out = []
        for line in lines[-limit:] if limit else lines:
            with contextlib.suppress(ValueError):
                out.append(json.loads(line))
        return out
