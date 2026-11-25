---
name: dispatcher-tasks
description: Queue and place work for agent sessions with dispatcher-tasks-for-agents — use when the user asks to queue, schedule, delegate or run a task later or in the background, when a task is too big for the current usage window, or when deciding which configured agent should do a piece of work.
---

# Using the dispatcher

The dispatcher (`dispatcher.py` in the folder where it was installed; its home is `~/.config/dispatcher-tasks` or
`$DISPATCHER_HOME`) runs agent sessions from a queue. You are the orchestrator: you write the brief, decide the size,
and put the task in the queue. The dispatcher decides *when* and *on which worker* it runs.

## Rules

1. **Urgency is mandatory.** Every task is `--urgent` or `--normal`.
   - Urgent: something is broken for the user now, or they said it is urgent.
   - Normal: everything else (features, research, cleanup).
   - **If it is unclear whether a task is urgent, ask the user. Never guess.**
2. **Size it yourself** while writing the brief: S (≈3 % of a usage window), M (≈10 %), L (≈25 %), XL (≈50 %).
   The dispatcher learns real sizes from finished tasks.
3. **Normal tasks go to the worker with the most weekly headroom**, even if another worker has room in its short
   window right now, so no worker is drained before the others (workers with unknown limits: the one used least this
   week). If that worker's short window can't fit the task, the task waits for that window to reset; it is not pushed
   to another worker.
4. **Urgent tasks** run now where they fit; between two that fit, the one with more weekly headroom.
5. **One task at a time per worker.** Never hand a worker several tasks at once: a task that overruns the window is
   cut off and its prompt cache is lost. Waiting for a reset is fine.
6. **Related work goes to the same place.** Before adding a task, look at what is running and queued
   (`queue list`). If the new task is part of work already running or queued, add it with `--with <id>` so it
   continues in the same session after the current one.
7. **No limit bypassing.** Do not add workers, accounts or keys to get around a limit. A task that hits a limit
   resumes by itself after the reset.
8. **Never touch credentials.** Workers use the user's own sign-in or API key from their environment.

## Commands

```bash
python3 dispatcher.py queue add <id> --brief-file <path> --size S|M|L|XL --urgent|--normal \
    [--needs <worker>|any] [--with <related-id>] [--title "…"] [--cwd <dir>]
python3 dispatcher.py queue list            # running and waiting tasks, and why each one waits
python3 dispatcher.py queue show <id>       # status, worker, last report
python3 dispatcher.py queue rm <id>
python3 dispatcher.py limits                # what each worker has left (when the agent reports it)
python3 dispatcher.py tick [--dry-run]      # one scheduling step (the background job runs this every few minutes)
```

## Writing a brief

- What to do, where (files, folders), and what "done" looks like.
- What not to do (live systems, spending money, pushing, messaging people) unless the user said so.
- Ask for a final report: what was done, **all errors first**, what was not checked, changed files.

## After a task finishes

Read its report (`queue show <id>`), check the result yourself before telling the user it is done, and tell the user
about every error the report lists.
