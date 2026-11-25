#!/usr/bin/env python3
"""dispatcher-tasks-for-agents — a task queue for AI coding agents (works with Claude Code, Codex CLI, Gemini CLI).

    python3 dispatcher.py init
    python3 dispatcher.py queue add <id> --brief-file brief.md --size S|M|L|XL --urgent|--normal [--needs W] [--with ID]
    python3 dispatcher.py queue list | show <id> | rm <id>
    python3 dispatcher.py limits
    python3 dispatcher.py tick [--dry-run]

Home: $DISPATCHER_HOME or ~/.config/dispatcher-tasks. See README.md.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from taskdispatch.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
