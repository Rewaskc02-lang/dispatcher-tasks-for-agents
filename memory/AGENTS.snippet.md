<!-- BEGIN dispatcher-tasks -->
## Dispatcher (dispatcher-tasks-for-agents)

When the user asks to queue, schedule, delegate or run work later/in the background, or a task is too big for the
current usage window, put it in the dispatcher queue instead of doing it now
(`python3 <install dir>/dispatcher.py queue add <id> --brief-file <path> --size S|M|L|XL --urgent|--normal`).

- Urgency is mandatory: urgent = broken now or the user said so; normal = everything else. **If unclear, ask the user.**
- Size it yourself: S ≈3 %, M ≈10 %, L ≈25 %, XL ≈50 % of a usage window.
- Normal tasks go to the worker with the most weekly headroom; if its short window can't fit the task, it waits for
  that reset. Urgent tasks run now where they fit.
- One task at a time per worker; never stack several.
- Related work: check `queue list`; if the task belongs to running/queued work, add it with `--with <id>`.
- Never add accounts or keys to get around limits; never touch credentials.
- Briefs: what, where, what "done" looks like, what not to do, and a final report with all errors first.
- After a task: read `queue show <id>`, verify the result, tell the user every error.
<!-- END dispatcher-tasks -->
