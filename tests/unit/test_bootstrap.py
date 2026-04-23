"""Tests for early process bootstrap helpers."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

from src import bootstrap


def test_ensure_safe_working_directory_keeps_valid_cwd() -> None:
    with patch("src.bootstrap.os.getcwd", return_value="/safe/current") as getcwd:
        assert bootstrap.ensure_safe_working_directory() == "/safe/current"

    getcwd.assert_called_once_with()


def test_ensure_safe_working_directory_recovers_from_invalid_cwd() -> None:
    with (
        patch("src.bootstrap.os.getcwd", side_effect=PermissionError("denied")),
        patch("src.bootstrap._iter_safe_workdirs", return_value=["/safe/fallback"]),
        patch("src.bootstrap._is_accessible_directory", return_value=True),
        patch("src.bootstrap.os.chdir") as chdir,
        patch.dict("src.bootstrap.os.environ", {}, clear=True),
    ):
        assert bootstrap.ensure_safe_working_directory() == "/safe/fallback"
        assert os.environ.get("PWD") == "/safe/fallback"

    chdir.assert_called_once_with("/safe/fallback")


def test_ensure_safe_working_directory_raises_when_no_candidate_is_usable() -> None:
    with (
        patch("src.bootstrap.os.getcwd", side_effect=PermissionError("denied")),
        patch("src.bootstrap._iter_safe_workdirs", return_value=["/bad"]),
        patch("src.bootstrap._is_accessible_directory", return_value=False),
    ):
        try:
            bootstrap.ensure_safe_working_directory()
        except RuntimeError as exc:
            assert "invalid current working directory" in str(exc)
        else:  # pragma: no cover - defensive failure path
            raise AssertionError("expected RuntimeError")


def test_iter_safe_workdirs_prefers_override_and_deduplicates() -> None:
    with (
        patch.dict("src.bootstrap.os.environ", {"AFM_SAFE_CWD": "/safe/override"}, clear=True),
        patch.object(bootstrap, "__file__", "/safe/override/bootstrap.py"),
        patch("src.bootstrap.Path.home", return_value=Path("/safe/home")),
        patch("src.bootstrap.tempfile.gettempdir", return_value="/safe/override"),
    ):
        workdirs = bootstrap._iter_safe_workdirs()

    assert workdirs == ["/safe/override", "/safe/home"]


def test_server_main_normalizes_cwd_before_delegating() -> None:
    calls: list[str] = []

    def fake_main() -> None:
        calls.append("server")

    fake_module = SimpleNamespace(main=fake_main)

    with (
        patch("src.bootstrap.ensure_safe_working_directory") as ensure,
        patch.dict(sys.modules, {"src.presentation.server": cast("object", fake_module)}),
    ):
        bootstrap.server_main()

    ensure.assert_called_once_with()
    assert calls == ["server"]


def test_direct_run_main_normalizes_cwd_before_delegating() -> None:
    calls: list[str] = []

    def fake_main() -> int:
        calls.append("direct-run")
        return 456

    fake_module = SimpleNamespace(main=fake_main)

    with (
        patch("src.bootstrap.ensure_safe_working_directory") as ensure,
        patch.dict(sys.modules, {"src.presentation.direct_run": cast("object", fake_module)}),
    ):
        assert bootstrap.direct_run_main() == 456

    ensure.assert_called_once_with()
    assert calls == ["direct-run"]
