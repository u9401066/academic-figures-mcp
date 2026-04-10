#!/usr/bin/env python3
"""Pre-commit hook: block commits with more than MAX_FILES changed files.

Exemptions: uv.lock, htmlcov/*, memory-bank/*, *.md (docs)
Override:   git commit --no-verify
"""

from __future__ import annotations

import subprocess

MAX_FILES = 30

EXEMPT_PATTERNS = (
    "uv.lock",
    "htmlcov/",
    "memory-bank/",
)


def _is_exempt(path: str) -> bool:
    return any(path.startswith(p) or path == p for p in EXEMPT_PATTERNS)


def main() -> int:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRT"],
        capture_output=True,
        text=True,
        check=False,
    )
    files = [f for f in result.stdout.strip().splitlines() if not _is_exempt(f)]

    if len(files) > MAX_FILES:
        print(
            f"\n❌ Commit blocked: {len(files)} files staged (max {MAX_FILES}).\n"
            f"   Split into smaller, focused commits.\n"
            f"   Emergency bypass: git commit --no-verify\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
