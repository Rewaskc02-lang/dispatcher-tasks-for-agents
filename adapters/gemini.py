"""Google Gemini CLI (`gemini`) — start; "continue" is a new run with the last report. NOT VERIFIED LIVE: built from the
official docs (Gemini CLI "Headless mode" and CLI reference); please report what you see on a real run.

* start: ``gemini --output-format json [-m MODEL] [args…]`` with the brief on stdin (a non-TTY run is headless)
* report: the JSON object's ``response``; a failure: its ``error`` object, or a non-zero exit code (documented: 1 — error
  or API failure, 42 — input error, 53 — turn limit exceeded); it counts as a *limit* when the message mentions a quota or
  rate limit (the exact wording is not documented)
* resume: the CLI has ``--resume <session>``, but the docs do not say where the JSON output gives the session id, so this
  adapter does not resume — the dispatcher starts a new run with a "continue" brief and the last report. A contribution
  that reads the session id (``--output-format stream-json``, its ``init`` event) is welcome.
* limits: not reported by the CLI — configure the worker's windows yourself (the plans have daily request caps).

Approvals for unattended runs are yours to choose — put the flags in the worker's ``args`` (for example
``["--approval-mode", "auto_edit"]``). Sign-in: your own (Google sign-in, or ``GEMINI_API_KEY`` / ``GOOGLE_API_KEY`` in your
environment with ``"auth": "api"``).
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from adapters.base import DONE, ERROR, LIMIT, LIMIT_WORDS, Outcome, ProcessAdapter

EXIT_WORDS = {42: "input error (invalid prompt or arguments)", 53: "turn limit exceeded"}


def _object(out: str) -> Dict[str, Any]:
    text = out.strip()
    start = text.find("{")
    while start != -1:
        try:
            obj = json.loads(text[start:])
            return obj if isinstance(obj, dict) else {}
        except ValueError:
            start = text.find("{", start + 1)
    return {}


class GeminiAdapter(ProcessAdapter):
    name = "gemini"
    binary = "gemini"
    can_resume = False
    KEY_VARS = ("GEMINI_API_KEY", "GOOGLE_API_KEY")

    def command(self, task: Dict[str, Any], *, resume: bool, text: str) -> Tuple[List[str], Optional[str]]:
        argv = self.bin() + ["--output-format", "json"]
        if self.worker.get("model"):
            argv += ["-m", str(self.worker["model"])]
        return argv + self.extra(), text

    def parse(self, out: str, err: str, code: int) -> Outcome:
        data = _object(out)
        report = str(data.get("response") or "")
        error = data.get("error")
        message = (str(error.get("message") or error) if isinstance(error, dict) else str(error or "")) or \
            (err.strip() if code != 0 else "")
        o = Outcome(DONE, code, report)
        if error or code != 0:
            o.status = LIMIT if LIMIT_WORDS.search(message) else ERROR
            o.why = (EXIT_WORDS.get(code) or (message.strip().splitlines()[-1:] or [f"exit code {code}"])[0])[:300]
        return o
