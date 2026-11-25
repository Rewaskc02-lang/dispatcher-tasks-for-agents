"""Stands for `claude -p --output-format stream-json --verbose`: init, rate_limit_event, result."""
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(__file__))
from _common import mode, record  # noqa: E402

argv = sys.argv[1:]
text = sys.stdin.read()
record(text)
session = argv[argv.index("--session-id") + 1] if "--session-id" in argv else \
    argv[argv.index("--resume") + 1] if "--resume" in argv else str(uuid.uuid4())
now = time.time()
used5 = float(os.environ.get("FAKE_USED", "0.30"))
print(json.dumps({"type": "system", "subtype": "init", "session_id": session}))
status = "rejected" if mode() == "limit" else "allowed"
print(json.dumps({"type": "rate_limit_event", "rate_limit_info": {"status": status, "resetsAt": int(now + 3600), "unifiedWindows": {
    "five_hour": {"utilization": 1.0 if mode() == "limit" else used5, "resetsAt": int(now + 3600), "status": status},
    "seven_day": {"utilization": 0.2, "resetsAt": int(now + 3 * 86400), "status": "allowed"}}}}))
if mode() == "limit":
    print(json.dumps({"type": "result", "subtype": "success", "is_error": True, "session_id": session,
                      "result": "You've hit your limit · resets 3pm"}))
    sys.exit(1)
if mode() == "error":
    print("boom", file=sys.stderr)
    sys.exit(2)
word = "resumed" if "--resume" in argv else "started"
print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "session_id": session, "total_cost_usd": 0.25,
                  "result": f"{word}: done — {text[:40]}"}))
