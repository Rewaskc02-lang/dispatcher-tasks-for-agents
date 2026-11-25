"""Shared by the fake agents: what they were called with goes to $FAKE_LOG (one JSON line per call)."""
import json
import os
import sys


def record(stdin_text):
    path = os.environ.get("FAKE_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"argv": sys.argv[1:], "stdin": stdin_text, "cwd": os.getcwd(),
                                 "keys": sorted(k for k in os.environ if k.endswith("_API_KEY"))}) + "\n")


def mode():
    return os.environ.get("FAKE_MODE", "done")
