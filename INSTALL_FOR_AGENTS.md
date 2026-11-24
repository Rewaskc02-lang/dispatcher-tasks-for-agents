# Installing dispatcher-tasks-for-agents (instructions for an AI coding agent)

This file is written for an AI coding agent (Claude Code, Codex CLI, Gemini CLI, …) that a user has asked to
install this project. Follow it step by step. Talk to the user in their language. Do not skip the questions marked
**ASK** — they are the user's decisions, not yours.

The dispatcher is a task scheduler for agent sessions: a queue with urgency, task sizes, runs after a usage window
resets, one task at a time per worker, and related work continued in the same session. It does **not** bypass usage
limits, switch accounts, or touch credentials: every worker is an agent CLI the user is already signed in to (or an API
key the user set in their own environment).

## 0. Before you start

1. Tell the user in two or three sentences what will be installed and where (see step 2), and that nothing runs in the
   background until they agree in step 6.
2. Check the prerequisites and report what is missing (do not install system packages without **ASK**):
   - `python3 --version` → 3.9 or newer;
   - `git --version`;
   - which agent CLIs exist on this machine: `claude --version`, `codex --version`, `gemini --version`
     (any subset is fine; at least one is needed).

## 1. Get the code

**ASK** where to put it (default: `~/dispatcher-tasks-for-agents`). Then:

```bash
git clone https://github.com/neemphy/dispatcher-tasks-for-agents.git ~/dispatcher-tasks-for-agents
cd ~/dispatcher-tasks-for-agents
python3 -m unittest discover -s tests
```

All tests must pass. If they don't, stop and show the user the failing lines — do not edit the project to make them pass.

## 2. Configure workers

```bash
python3 dispatcher.py init
```

`init` writes `~/.config/dispatcher-tasks/config.json` (or the path in `DISPATCHER_HOME`) and asks nothing by itself —
you fill it with the user's answers:

- **ASK** which of the agents found in step 0 the dispatcher may use. One worker per agent the user has.
- For each worker: does the user sign in with a subscription (the agent's own login) or with an API key from their
  environment? **Never** ask for, copy, print or store a password, token or key — the dispatcher only starts the
  agent CLI, which uses the user's own sign-in.
- Windows/limits: the `claude` adapter reads its windows from the CLI; for others **ASK** whether they know their plan's
  limits (window length, weekly quota) or leave them as `unknown` (then the dispatcher just runs one task at a time and
  pauses after a limit is hit).

Show the user the final config (it contains no secrets) and get an OK.

## 3. Teach the orchestrating agent the rules (memory)

The rules for *using* the dispatcher live in this repo. Install them where the user's agent reads standing instructions.
**ASK** before writing outside the project folder, and show the user what you add.

| Agent | Where | How |
|---|---|---|
| Claude Code | `~/.claude/skills/dispatcher-tasks/SKILL.md` | copy `skills/dispatcher-tasks/SKILL.md` (a Claude Code skill — loaded when relevant) |
| Codex CLI | `~/.codex/AGENTS.md` | append the block from `memory/AGENTS.snippet.md` (between its markers) |
| Gemini CLI | `~/.gemini/GEMINI.md` | append the same block from `memory/AGENTS.snippet.md` |

If a file already exists, append — never overwrite the user's own instructions. Keep the `BEGIN/END dispatcher-tasks`
markers so the block can be updated or removed later.

## 4. Dry run

```bash
python3 dispatcher.py queue add hello-test --size S --normal --needs any --dry-run \
  --brief "Reply with the word OK and nothing else."
python3 dispatcher.py tick --dry-run
python3 dispatcher.py queue list
```

Explain to the user what the dry run says it *would* do (which worker, why, or why it waits). Then remove the test:
`python3 dispatcher.py queue rm hello-test`.

## 5. One real tiny task (optional)

**ASK** whether to run one tiny real task (it uses a little of the user's plan or API budget). If yes, add it without
`--dry-run`, run `python3 dispatcher.py tick`, wait, and show `python3 dispatcher.py queue show hello-test`.

## 6. Background tick (optional)

The queue only moves when `tick` runs. **ASK** whether to run it every 5 minutes in the background. If yes, install the
example for this OS and show the user how to stop it:

- macOS: `examples/launchd/dispatcher-tasks.tick.plist` → `~/Library/LaunchAgents/`, then
  `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/dispatcher-tasks.tick.plist`
- Linux: `examples/systemd/dispatcher-tasks-tick.{service,timer}` → `~/.config/systemd/user/`, then
  `systemctl --user enable --now dispatcher-tasks-tick.timer`
- elsewhere: a cron line from `examples/cron.txt`.

## 7. Finish

Tell the user: where it is installed, which workers are configured, whether the background tick is on, where the
events log is (`events.jsonl` in the dispatcher home), and how to uninstall (step 8). Point them to the Terms section of
`README.md`: they are responsible for using each agent within its provider's terms.

## 8. Uninstall

Stop the background tick (the reverse of step 6), remove the memory block between the `BEGIN/END dispatcher-tasks`
markers (or the skill folder), delete the dispatcher home and the cloned folder. Nothing else is installed.
