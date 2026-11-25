"""OpenAI Codex CLI (`codex`) — start and resume the same session. NOT VERIFIED LIVE: built from the official docs
(Codex "Non-interactive mode" and CLI reference); please report what you see on a real run.

* start:  ``codex exec --json [-m MODEL] [args…] -`` — the brief on stdin (``-`` = read the prompt from stdin)
* session: the ``thread.started`` event's ``thread_id``
* resume: ``codex exec --json [-m MODEL] [args…] resume <thread_id> "<follow-up>"`` (the follow-up as an argument: the docs
  do not say whether ``resume`` reads stdin)
* report: the text of the last ``item.completed`` whose item is an ``agent_message``
* a failed run: a ``turn.failed`` or ``error`` event, or a non-zero exit code; it counts as a *limit* when its message
  mentions a usage/rate limit or quota (the exact wording is not documented)
* limits: not reported by the CLI — configure the worker's windows yourself, or leave them unknown.

Sandbox and approvals for unattended runs are yours to choose — put the flags in the worker's ``args`` (for example
``["--sandbox", "workspace-write"]``; ``--skip-git-repo-check`` outside a git repository). Sign-in: your own (ChatGPT
sign-in, or ``CODEX_API_KEY`` in your environment with ``"auth": "api"``).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from adapters.base import DONE, ERROR, LIMIT, LIMIT_WORDS, Outcome, ProcessAdapter, json_lines


def _message(ev: Dict[str, Any]) -> str:
    err = ev.get("error")
    if isinstance(err, dict):
        return str(err.get("message") or err)
    return str(err or ev.get("message") or "")


class CodexAdapter(ProcessAdapter):
    name = "codex"
    binary = "codex"
    can_resume = True
    KEY_VARS = ("CODEX_API_KEY", "OPENAI_API_KEY")

    def command(self, task: Dict[str, Any], *, resume: bool, text: str) -> Tuple[List[str], Optional[str]]:
        argv = self.bin() + ["exec", "--json"]
        if self.worker.get("model"):
            argv += ["-m", str(self.worker["model"])]
        argv += self.extra()
        if resume:
            return argv + ["resume", task["session"], text], None
        return argv + ["-"], text

    def parse(self, out: str, err: str, code: int) -> Outcome:
        events = json_lines(out)
        session = next((str(e.get("thread_id")) for e in events if e.get("type") == "thread.started" and e.get("thread_id")), "")
        report = ""
        for e in events:
            item = e.get("item") if isinstance(e.get("item"), dict) else {}
            if e.get("type") == "item.completed" and item.get("type") == "agent_message":
                report = str(item.get("text") or "")
        failures = [_message(e) for e in events if e.get("type") in ("turn.failed", "error")]
        o = Outcome(DONE, code, report, session)
        problem = " ".join(failures) or (err if code != 0 else "")
        if failures or code != 0:
            o.status = LIMIT if LIMIT_WORDS.search(problem) else ERROR
            o.why = (problem.strip().splitlines()[-1:] or [f"exit code {code}"])[0][:300]
        return o
