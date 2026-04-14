"""Container dependency wiring smoke tests."""

from __future__ import annotations

from unittest.mock import patch

from src.presentation.dependencies import Container


class TestContainerReset:
    """Verify _reset_for_testing clears the singleton."""

    def teardown_method(self) -> None:
        Container._reset_for_testing()

    @patch("src.presentation.dependencies.load_config")
    def test_reset_creates_fresh_instance(self, mock_cfg: object) -> None:
        first = Container.get()
        Container._reset_for_testing()
        second = Container.get()
        assert first is not second

    @patch("src.presentation.dependencies.load_config")
    def test_get_returns_same_instance(self, mock_cfg: object) -> None:
        a = Container.get()
        b = Container.get()
        assert a is b
