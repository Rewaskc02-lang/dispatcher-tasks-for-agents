"""Stands for `codex exec --json …`: JSONL events per the Codex docs (thread.started, item.completed, turn.completed)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import mode, record  # noqa: E402

argv = sys.argv[1:]
resume = "resume" in argv
text = argv[-1] if resume else sys.stdin.read()
record(text)
thread = argv[argv.index("resume") + 1] if resume else "thread-123"
print(json.dumps({"type": "thread.started", "thread_id": thread}))
print(json.dumps({"type": "turn.started"}))
if mode() == "limit":
    print(json.dumps({"type": "turn.failed", "error": {"message": "You've hit your usage limit. Try again later."}}))
    sys.exit(1)
print(json.dumps({"type": "item.completed", "item": {"id": "item_1", "type": "agent_message",
                                                       "text": ("resumed" if resume else "started") + f": {text[:40]}"}}))
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 0, "output_tokens": 5}}))
