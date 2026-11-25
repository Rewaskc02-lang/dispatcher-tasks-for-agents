"""The command line of ``dispatcher.py``."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import adapters
from taskdispatch import windows as win
from taskdispatch.home import SIZES, Home, now, write_json
from taskdispatch.scheduler import Scheduler

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
HELP = {
    "workers": "One entry per agent you use. enabled — may the dispatcher start it; auth — 'subscription' (the agent's own "
               "sign-in) or 'api' (an API key you set in your own environment; the dispatcher never reads it); model, args — "
               "added to the agent's command (approval/sandbox flags for unattended runs go into args).",
    "windows": "'reported' — the agent's output says how much of its windows is used (claude); or a list like "
               "[{\"name\": \"short\", \"hours\": 5}, {\"name\": \"week\", \"hours\": 168}] — counted from this dispatcher's own "
               "runs; or leave it out — unknown: one task at a time and a pause after a limit is hit.",
    "budget_usd": "For API keys: {\"amount\": 5, \"hours\": 24} — money instead of windows (agents that report cost).",
    "reserve_percent": "Share of the short window kept free for your own use (default 10).",
}


def default_worker(agent: str, found: bool) -> Dict[str, Any]:
    w: Dict[str, Any] = {"name": agent, "agent": agent, "enabled": found, "auth": "subscription", "model": None, "args": [],
                         "reserve_percent": 10, "pause_after_limit_minutes": 60}
    if agent == "claude":
        w.update(windows="reported", probe_minutes=10)
    return w


def cmd_init(home: Home, force: bool) -> int:
    if home.config_path.exists() and not force:
        print(f"{home.config_path} exists — not changed (use --force to write a fresh one)")
        return 0
    found = {a: shutil.which(a) is not None for a in adapters.ADAPTERS}
    cfg = {"_help": HELP, "workers": [default_worker(a, found[a]) for a in adapters.ADAPTERS]}
    write_json(home.config_path, cfg)
    print(f"wrote {home.config_path}")
    for a, ok in found.items():
        print(f"  {a:7s} {'found on PATH — enabled' if ok else 'not found — disabled'}")
    print("Edit it with the user's answers (which agents, subscription or API key, known limits). It holds no secrets.")
    return 0


def read_brief(a: argparse.Namespace) -> str:
    if a.brief_file:
        return Path(a.brief_file).expanduser().read_text(encoding="utf-8")
    return a.brief or ""


def cmd_limits(sched: Scheduler, probe: bool) -> int:
    st = sched.home.state()
    if probe:
        sched.refresh_limits(st)
    views = sched.views(st)
    at = now()
    for w in sched.workers():
        v = views.get(w["name"])
        if v is None:
            continue
        parts = [f"{w['name']:10s} [{v.source}]"]
        for label, x in (("short", v.short), ("long", v.long)):
            if x is not None:
                parts.append(f"{label}: {x.used:.0f} % used, resets {win.clock(x.resets, at)}")
        if v.paused_until > at:
            parts.append(f"paused after a limit, until {win.clock(v.paused_until, at)}")
        if v.source == "unknown":
            parts.append("limits unknown — one task at a time")
        parts.append(f"started here in 7 days: {v.recent:.0f} % of a short window")
        print("  ·  ".join(parts))
    return 0


def main(argv: Optional[List[str]] = None, *, home: Optional[Home] = None) -> int:
    ap = argparse.ArgumentParser(prog="dispatcher.py", description="A task queue for AI coding agents.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init", help="write a starting config in the dispatcher home")
    p.add_argument("--force", action="store_true")
    q = sub.add_parser("queue", help="the queue")
    qs = q.add_subparsers(dest="qcmd", required=True)
    a = qs.add_parser("add", help="queue a task")
    a.add_argument("id")
    b = a.add_mutually_exclusive_group(required=True)
    b.add_argument("--brief-file", help="a file with the brief")
    b.add_argument("--brief", help="the brief as text")
    a.add_argument("--size", required=True, choices=list(SIZES))
    u = a.add_mutually_exclusive_group()
    u.add_argument("--urgent", dest="urgent", action="store_const", const=True)
    u.add_argument("--normal", dest="urgent", action="store_const", const=False)
    a.add_argument("--needs", default="any", help="a worker name, or any (default)")
    a.add_argument("--with", dest="with_id", default="", help="part of this task: continue its session after it")
    a.add_argument("--alone", action="store_true", help="do not link it to similar running/queued work")
    a.add_argument("--title", default="")
    a.add_argument("--cwd", default="", help="the folder the agent works in (default: the current folder)")
    a.add_argument("--dry-run", action="store_true", help="record it as a test entry: tick shows what it would do, never starts it")
    qs.add_parser("list", help="running, waiting (and why), recently finished")
    s = qs.add_parser("show", help="one task: status, runs, last report")
    s.add_argument("id")
    r = qs.add_parser("rm", help="remove a waiting task")
    r.add_argument("id")
    lm = sub.add_parser("limits", help="what each worker has left")
    lm.add_argument("--no-probe", action="store_true", help="only cached numbers, no request to the agent")
    t = sub.add_parser("tick", help="one scheduling step (run it every few minutes)")
    t.add_argument("--dry-run", action="store_true", help="show what it would do; change nothing")
    rr = sub.add_parser("_run", help=argparse.SUPPRESS)
    rr.add_argument("run_dir")
    args = ap.parse_args(argv)
    home = home or Home()
    try:
        if args.cmd == "init":
            return cmd_init(home, args.force)
        if args.cmd == "_run":
            from taskdispatch import runner
            return runner.run(Path(args.run_dir))
        sched = Scheduler(home)
        if args.cmd == "tick":
            sched.tick(dry=args.dry_run)
            return 0
        if args.cmd == "limits":
            return cmd_limits(sched, not args.no_probe)
        if args.qcmd == "add":
            if not ID_RE.match(args.id):
                raise SystemExit("the id may hold letters, digits, '.', '_' and '-' (up to 80)")
            _, lines = sched.add(args.id, read_brief(args), size=args.size, urgent=args.urgent, needs=args.needs,
                                 with_id=args.with_id, alone=args.alone, title=args.title, cwd=args.cwd, dry=args.dry_run)
            print("\n".join(lines))
            return 0
        if args.qcmd == "list":
            print("\n".join(sched.listing()))
            return 0
        if args.qcmd == "show":
            info = sched.show(args.id)
            report = info.pop("report", "") or ""
            brief = info.pop("brief", "") or ""
            print(json.dumps(info, ensure_ascii=False, indent=1))
            if brief:
                print("\n--- brief ---\n" + brief)
            if report:
                print("\n--- last report ---\n" + report)
            return 0 if info.get("state") != "unknown" else 1
        if args.qcmd == "rm":
            sched.remove(args.id)
            print(f"{args.id}: removed")
            return 0
    except SystemExit as exc:
        if isinstance(exc.code, str):
            print(f"dispatcher: {exc.code}", file=sys.stderr)
            return 2
        raise
    except OSError as exc:
        print(f"dispatcher: {exc}", file=sys.stderr)
        return 2
    return 2
