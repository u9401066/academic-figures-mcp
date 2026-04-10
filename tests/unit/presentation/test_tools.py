from __future__ import annotations

from typing import TYPE_CHECKING, cast

from src.presentation import tools
from src.presentation.dependencies import Container

if TYPE_CHECKING:
    from pytest import MonkeyPatch

    from src.application.generate_figure import GenerateFigureRequest


def test_generate_figure_rejects_invalid_pmid(monkeypatch: MonkeyPatch) -> None:
    def fail_container_get() -> object:
        raise AssertionError("container should not run")

    monkeypatch.setattr(Container, "get", fail_container_get)

    result = tools.generate_figure(pmid="pmid-abc")

    assert result["status"] == "error"
    assert "digits" in str(result["error"])


def test_plan_figure_rejects_invalid_output_size(monkeypatch: MonkeyPatch) -> None:
    def fail_container_get() -> object:
        raise AssertionError("container should not run")

    monkeypatch.setattr(Container, "get", fail_container_get)

    result = tools.plan_figure(pmid="12345678", output_size="huge")

    assert result["status"] == "error"
    assert "output_size" in str(result["error"])


def test_generate_figure_accepts_planned_payload(monkeypatch: MonkeyPatch) -> None:
    class StubGenerateUseCase:
        def __init__(self) -> None:
            self.request: object | None = None

        def execute(self, req: object) -> dict[str, str]:
            self.request = req
            return {"status": "ok", "asset_kind": "repo_icon"}

    class StubContainer:
        def __init__(self) -> None:
            self.generate_use_case = StubGenerateUseCase()

        def generate_figure_uc(self) -> StubGenerateUseCase:
            return self.generate_use_case

    container = StubContainer()
    monkeypatch.setattr(Container, "get", lambda: container)

    payload = {
        "asset_kind": "repo_icon",
        "goal": "Create a bold repo icon",
        "selected_figure_type": "infographic",
        "render_route": "image_generation",
        "language": "en",
        "output_size": "1024x1024",
        "prompt_pack": {"prompt": "repo icon prompt"},
    }

    result = tools.generate_figure(
        planned_payload=payload,
        output_dir="brand-output",
        target_journal="Nature",
    )

    assert result["status"] == "ok"
    request = cast("GenerateFigureRequest", container.generate_use_case.request)
    assert request is not None
    assert request.pmid is None
    assert request.planned_payload == payload
    assert request.output_dir == "brand-output"
    assert request.target_journal == "Nature"


def test_composite_figure_rejects_mismatched_labels() -> None:
    result = tools.composite_figure(
        panels=[["panel-a.png", "anatomy"]],
        labels=["A", "B"],
        title="Composite",
    )

    assert result["status"] == "error"
    assert "same length" in str(result["error"])
