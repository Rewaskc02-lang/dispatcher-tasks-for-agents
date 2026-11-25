"""A starting point for an adapter of your own agent — copy this file to ``adapters/<agent>.py`` and fill in the three
marked places. See CONTRIBUTING.md for the checklist and the tests to add.

What the scheduler needs from an adapter (adapters/base.py):

    start(task) -> run id          ProcessAdapter does it: runs ``command(...)`` in the background, brief on stdin
    resume(run, text, task)        only if ``can_resume = True`` (the agent can continue a session by its id)
    status(run) -> Outcome         ProcessAdapter does it: running until the process ends, then ``parse(...)``
    report(run) -> str             the Outcome's ``report``
    limits() -> dict | None        optional; return None unless the agent itself tells how much of its limits is used

Rules every adapter keeps:
* start the agent's own, unmodified program; never read, store or pass on a password, token or key;
* list the agent's API-key environment variables in ``KEY_VARS`` (they are removed for ``"auth": "subscription"``);
* do not guess flags — take them from the agent's official docs or ``--help`` and say in the module docstring which ones
  and whether the adapter was verified live.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from adapters.base import DONE, ERROR, LIMIT, LIMIT_WORDS, Outcome, ProcessAdapter


class MyAgentAdapter(ProcessAdapter):
    name = "myagent"                    # 1) the "agent" name used in config.json (also add it to ADAPTERS in __init__.py)
    binary = "myagent"                  #    the program; a worker's "bin" overrides it
    can_resume = False                  #    True only if command(resume=True) really continues the same session
    KEY_VARS: Tuple[str, ...] = ()      #    e.g. ("MYAGENT_API_KEY",)

    def new_session(self) -> str:
        """If the agent lets you choose the session id up front (like ``--session-id``), return a new one here; otherwise
        return '' and set ``Outcome.session`` in parse() from the agent's output."""
        return ""

    def command(self, task: Dict[str, Any], *, resume: bool, text: str) -> Tuple[List[str], Optional[str]]:
        """2) The non-interactive command. Return (argv, stdin): the brief usually goes on stdin; ``task["session"]`` holds
        the session id for a resume. Add the user's ``model`` and ``args`` from the worker config."""
        argv = self.bin()
        if self.worker.get("model"):
            argv += ["--model", str(self.worker["model"])]
        return argv + self.extra(), text

    def parse(self, out: str, err: str, code: int) -> Outcome:
        """3) Read the finished run: the final text, the session id (for a resume), and whether it stopped at a usage
        limit (then the scheduler pauses this worker and continues the task after the reset)."""
        o = Outcome(DONE, code, out.strip())
        if code != 0:
            problem = err.strip() or out.strip()
            o.status = LIMIT if LIMIT_WORDS.search(problem) else ERROR
            o.why = (problem.splitlines()[-1:] or [f"exit code {code}"])[0][:300]
        return o
