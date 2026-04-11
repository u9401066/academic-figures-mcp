#!/usr/bin/env python3
"""Pre-commit hook: check agent/instruction files are not stale.

Warns if .github/agents/ or .github/copilot-instructions.md haven't been
updated in a long time while source code has been actively changed.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

STALE_DAYS = 90
AGENT_DIR = Path(".github/agents")
INSTRUCTIONS = Path(".github/copilot-instructions.md")

# ── i18n: English / 繁體中文 ──────────────────────────────────
_LANG = os.environ.get("LANG", "").lower()
_USE_ZH = "zh" in _LANG or "tw" in _LANG or _LANG.startswith("zh")

MSG_HEADER: str = "\n🔄 Agent Freshness Check:" if not _USE_ZH else "\n🔄 Agent 新鮮度檢查:"
MSG_FOOTER: str = (
    "   Consider reviewing and updating these files.\n"
    if not _USE_ZH
    else "   建議檢視並更新這些檔案.\n"
)
MSG_DAYS_AGO: str = "last updated {days} days ago"
MSG_DAYS_AGO_ZH: str = "上次更新於 {days} 天前"


def _git_last_modified(path: str) -> float | None:
    """Return last commit timestamp for a path, or None."""
    result = subprocess.run(
        ["git", "log", "-1", "--format=%ct", "--", path],
        capture_output=True,
        text=True,
        check=False,
    )
    out = result.stdout.strip()
    return float(out) if out else None


def main() -> int:
    now = time.time()
    stale_threshold = now - (STALE_DAYS * 86400)
    warnings: list[str] = []

    # Check agent files
    if AGENT_DIR.exists():
        for agent_file in AGENT_DIR.glob("*.agent.md"):
            ts = _git_last_modified(str(agent_file))
            if ts and ts < stale_threshold:
                days = int((now - ts) / 86400)
                age = (
                    MSG_DAYS_AGO.format(days=days)
                    if not _USE_ZH
                    else MSG_DAYS_AGO_ZH.format(days=days)
                )
                warnings.append(f"  ⚠️  {agent_file.name} — {age}")

    # Check instructions
    if INSTRUCTIONS.exists():
        ts = _git_last_modified(str(INSTRUCTIONS))
        if ts and ts < stale_threshold:
            days = int((now - ts) / 86400)
            age = (
                MSG_DAYS_AGO.format(days=days)
                if not _USE_ZH
                else MSG_DAYS_AGO_ZH.format(days=days)
            )
            warnings.append(f"  ⚠️  copilot-instructions.md — {age}")

    if warnings:
        print(MSG_HEADER)
        for w in warnings:
            print(w)
        print(MSG_FOOTER)

    # Non-blocking
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
