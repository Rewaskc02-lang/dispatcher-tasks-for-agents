"""One run in the background: ``python3 dispatcher.py _run <home>/runs/<task>/<n>``.

The adapter prepared the folder (meta.json: the command, the folder to work in, whether there is a stdin file). This
process starts the agent there with the brief on stdin, keeps its output (out.txt, err.txt), writes the exit code, and then
records the end of the run in the queue state (and an event). It runs in its own process group, so stopping it (``pid``)
stops the agent too.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from taskdispatch.home import Home, iso


def run(run_dir: Path) -> int:
    d = Path(run_dir).resolve()
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    home = Home(d.parents[2])                        # <home>/runs/<task>/<n>
    from taskdispatch.scheduler import Scheduler
    sched = Scheduler(home)
    worker = sched.worker(meta["worker"]) or {"name": meta["worker"], "agent": meta["agent"]}
    ad = sched.adapter(worker)
    (d / "pid").write_text(str(os.getpid()))
    (d / "started").write_text(iso())
    code = 127
    with open(d / "out.txt", "wb") as out, open(d / "err.txt", "wb") as err:
        stdin = open(d / "stdin.txt", "rb") if meta.get("stdin") else subprocess.DEVNULL
        try:
            code = subprocess.run(meta["argv"], cwd=meta["cwd"], stdin=stdin, stdout=out, stderr=err, env=ad.env()).returncode
        except OSError as exc:                       # no such program or folder
            err.write(f"dispatcher: could not start {meta['argv'][:1]} in {meta['cwd']}: {exc}\n".encode())
        finally:
            if stdin is not subprocess.DEVNULL:
                stdin.close()
    (d / "exit").write_text(str(code))
    outcome = ad.status(f"{meta['task']}/{meta['n']}")
    with home.changing() as st:
        sched.finish(st, meta["task"], int(meta["n"]), outcome)
    return code
