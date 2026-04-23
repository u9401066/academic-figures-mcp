"""Bootstrap console entry points with a safe working directory."""

from __future__ import annotations

import os
import tempfile
from contextlib import suppress
from pathlib import Path


def ensure_safe_working_directory() -> str:
    """Repair an invalid process cwd before importing heavy dependencies."""

    try:
        current = os.getcwd()
    except OSError:
        current = None

    if current:
        return current

    for candidate in _iter_safe_workdirs():
        if not _is_accessible_directory(candidate):
            continue
        os.chdir(candidate)
        os.environ["PWD"] = candidate
        return candidate

    raise RuntimeError("Unable to recover from an invalid current working directory")


def server_main() -> None:
    """Launch the MCP server after normalizing cwd."""

    ensure_safe_working_directory()

    from src.presentation.server import main

    main()


def direct_run_main() -> int | None:
    """Launch the direct-run CLI after normalizing cwd."""

    ensure_safe_working_directory()

    from src.presentation.direct_run import main

    return main()


def _iter_safe_workdirs() -> list[str]:
    candidates: list[str] = []

    override = os.environ.get("AFM_SAFE_CWD", "").strip()
    if override:
        candidates.append(override)

    with suppress(RuntimeError):
        candidates.append(str(Path.home()))

    candidates.append(tempfile.gettempdir())
    candidates.append(str(Path(__file__).resolve().parent))

    seen: set[str] = set()
    ordered: list[str] = []
    for candidate in candidates:
        candidate_key = _workdir_identity(candidate)
        if candidate_key in seen:
            continue
        seen.add(candidate_key)
        ordered.append(candidate)
    return ordered


def _workdir_identity(path: str) -> str:
    """Return a stable comparison key without depending on a valid cwd."""

    expanded = os.path.expanduser(path)
    with suppress(OSError, RuntimeError, ValueError):
        return os.path.normcase(os.path.abspath(expanded))
    return os.path.normcase(os.path.normpath(expanded))


def _is_accessible_directory(path: str) -> bool:
    candidate = Path(path)
    return candidate.is_dir() and os.access(candidate, os.R_OK | os.X_OK)
