#!/usr/bin/env python3
"""Pre-commit hook: remind to sync Memory Bank when source files changed."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

MEMORY_BANK_DIR = Path("memory-bank")
SRC_PATTERNS = ("src/",)

# ── i18n: English / 繁體中文 ──────────────────────────────────
_LANG = os.environ.get("LANG", "").lower()
_USE_ZH = "zh" in _LANG or "tw" in _LANG or _LANG.startswith("zh")

MSG_REMINDER: str = (
    "\n💡 Memory Bank Reminder: source files changed but memory-bank/ "
    "was not updated.\n"
    "   Consider running: UMB (Update Memory Bank) in your next session.\n"
    if not _USE_ZH else
    "\n💡 Memory Bank 提醒: 原始碼已變更但 memory-bank/ 未同步更新.\n"
    "   建議在下次工作階段執行: UMB (更新 Memory Bank)\n"
)


def main() -> int:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRT"],
        capture_output=True,
        text=True,
        check=False,
    )
    staged = result.stdout.strip().splitlines()

    src_changed = any(f.startswith(p) for f in staged for p in SRC_PATTERNS)
    mb_changed = any(f.startswith("memory-bank/") for f in staged)

    if src_changed and not mb_changed and MEMORY_BANK_DIR.exists():
        print(MSG_REMINDER)
        # Non-blocking — just a reminder
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
