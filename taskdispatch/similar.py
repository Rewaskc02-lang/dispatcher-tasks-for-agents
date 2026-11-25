"""Is a new task part of work that is already running or queued? An explicit ``--with <id>`` always wins; without it this is a
conservative hint by shared file paths and words of the briefs (a wrong link would put unrelated work into one session).
Use ``--alone`` to switch the hint off for a task."""
from __future__ import annotations

import re
from typing import Iterable, Tuple

PATH_RE = re.compile(r"(?:[\w.\-]+/)+[\w.\-]+|[\w\-]+\.(?:py|md|json|jsonl|ts|tsx|js|go|rs|java|rb|sh|sql|ya?ml|toml|html|css)\b")
WORD_RE = re.compile(r"[^\W\d_][\w]{4,}", re.UNICODE)
COMMON_PATHS = {"readme.md", "agents.md", "claude.md", "gemini.md", "changelog.md", "contributing.md"}
STOP = {"should", "about", "there", "which", "their", "would", "could", "these", "those", "please", "after", "before",
        "write", "check", "tests", "report", "every", "while", "where", "other", "files", "first", "start"}


def tokens(text: str) -> Tuple[set, set]:
    paths = {m.strip("./").lower() for m in PATH_RE.findall(text or "")}
    paths = {p for p in paths if p.rsplit("/", 1)[-1] not in COMMON_PATHS and len(p) > 3}
    names = {p.rsplit("/", 1)[-1] for p in paths}
    stems = {w.lower()[:6] for w in WORD_RE.findall(text or "")} - {s[:6] for s in STOP}
    return paths | names, stems


def similarity(a: str, b: str) -> Tuple[bool, str]:
    pa, wa = tokens(a)
    pb, wb = tokens(b)
    shared = sorted(pa & pb)
    jac = len(wa & wb) / max(1, len(wa | wb))
    related = (len(shared) >= 2 and jac >= 0.12) or (len(shared) >= 1 and jac >= 0.25) or jac >= 0.45
    return related, f"shared files: {', '.join(shared[:5]) or 'none'}; words overlap {jac:.0%}"


def find_related(text: str, candidates: Iterable[Tuple[str, str]]) -> Tuple[str, str]:
    """candidates: (id, brief). → (id, why) of the first related one, or ('', '')."""
    for cid, brief in candidates:
        ok, why = similarity(text, brief)
        if ok:
            return cid, why
    return "", ""
