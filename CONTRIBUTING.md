# Contributing

The most welcome contribution is an **adapter for another agent**. The scheduler (`taskdispatch/`) knows no agent at
all; everything agent-specific lives in one small file in `adapters/`.

## Writing an adapter

1. Copy `adapters/_template.py` to `adapters/<agent>.py` and rename the class.
2. Read the agent's **official documentation** and its `--help`. Do not guess flags. Write in the module docstring which
   flags you use, where they are documented, and whether you ran the adapter against the real agent ("verified live")
   or only against a fake.
3. Fill in the three places marked in the template:
   - `command(task, resume, text)` → `(argv, stdin)`: the agent's non-interactive command. The brief usually goes on
     stdin. Add the worker's `model` and `args`.
   - `parse(out, err, exit_code)` → `Outcome`: the final text (`report`), the session id if the agent has one
     (`session`), and the status: `done`, `error`, or `limit` when the run stopped at a usage limit (then the scheduler
     pauses this worker and continues the task after the reset).
   - `can_resume` / `new_session()`: set `can_resume = True` only if `command(resume=True)` really continues the same
     session. Otherwise the scheduler continues work with a new run that gets the original brief and the last report.
4. Optional: `limits()` → `{"short": {"used": %, "resets": unix time}, "long": {...}}` — only if the agent itself says how
   much of its limits is used, through an ordinary call of the same program. Then set `reported_windows`. If it can't,
   leave it out: users configure windows themselves or leave them unknown.
5. List the agent's API-key environment variables in `KEY_VARS` (they are removed from the run's environment for
   workers with `"auth": "subscription"`).
6. Register it: one line in `ADAPTERS` in `adapters/__init__.py`.
7. Add a row to the "Supported agents" table in `README.md`.

### Rules every adapter keeps

- One user, the user's own sign-in. Start the agent's unmodified program; never read, store or pass on a password,
  token, session cookie or API key.
- No account switching, pooling or rotating — the dispatcher waits for limits, it does not get around them.
- No network calls of its own: the agent program does the talking.

## Tests to add

Everything runs with `python3 -m unittest discover -s tests` — standard library only, no network, no real agent.

- `tests/fakes/fake_<agent>.py`: a tiny script that prints what the real agent prints in its non-interactive mode
  (use the documented format), records its argv and stdin through `tests/fakes/_common.py`, and fails with a
  limit message when `FAKE_MODE=limit`.
- In `tests/test_adapters.py`: the exact command for a start and a resume; `parse` of a normal run, an error and a
  limit; a successful report that merely *mentions* limits must stay `done`.
- In `tests/test_scheduler.py`: one end-to-end run through the scheduler with your fake (see the `Related` and
  `AfterALimit` tests for codex and gemini).

## Other changes

Keep Python 3.9 compatibility and the standard library only. If you change a command or an option, update `README.md`,
`INSTALL_FOR_AGENTS.md`, `skills/dispatcher-tasks/SKILL.md` and `memory/AGENTS.snippet.md` in the same change — agents
install and use the project from those files.
