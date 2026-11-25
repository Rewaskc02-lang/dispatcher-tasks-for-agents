"""Stands for `gemini --output-format json` (headless): one JSON object with response / stats / error."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import mode, record  # noqa: E402

text = sys.stdin.read()
record(text)
if mode() == "limit":
    print(json.dumps({"error": {"type": "ApiError", "message": "Quota exceeded: RESOURCE_EXHAUSTED (429)"}}))
    sys.exit(1)
print(json.dumps({"response": f"done: {text[:40]}", "stats": {"models": {}}}))
