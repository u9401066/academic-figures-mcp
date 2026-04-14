from __future__ import annotations

from typing import TYPE_CHECKING, cast

from src.application.list_manifests import ListManifestsRequest
from src.application.replay_manifest import ReplayManifestRequest
from src.application.retarget_journal import RetargetJournalRequest
from src.presentation import tools
from src.presentation.dependencies import Container

if TYPE_CHECKING:
    from pytest import MonkeyPatch

    from src.application.composite_figure import CompositeFigureRequest
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


def test_composite_figure_passes_request(monkeypatch: MonkeyPatch) -> None:
    class StubUseCase:
        def __init__(self) -> None:
            self.request: object | None = None

        def execute(self, req: object) -> dict[str, str]:
            self.request = req
            return {"status": "ok", "output_path": "out/composite.png"}

    class StubContainer:
        def __init__(self) -> None:
            self.uc = StubUseCase()

        def composite_figure_uc(self) -> StubUseCase:
            return self.uc

    container = StubContainer()
    monkeypatch.setattr(Container, "get", lambda: container)

    result = tools.composite_figure(
        panels=[[" panel-a.png ", " chart "], ["panel-b.png", ""]],
        labels=[" A ", "B"],
        title=" Composite ",
        caption=" Caption ",
        citation=" PMID:123 ",
        output_path=" out/composite.png ",
    )

    assert result["status"] == "ok"
    request = cast("CompositeFigureRequest", container.uc.request)
    assert request is not None
    assert request.panels == [
        {
            "prompt": "composite panel",
            "label": "A",
            "panel_type": "chart",
            "image_path": "panel-a.png",
        },
        {
            "prompt": "composite panel",
            "label": "B",
            "panel_type": "anatomy",
            "image_path": "panel-b.png",
        },
    ]
    assert request.title == "Composite"
    assert request.caption == "Caption"
    assert request.citation == "PMID:123"
    assert request.output_path == "out/composite.png"


def test_replay_manifest_passes_request(monkeypatch: MonkeyPatch) -> None:
    class StubUseCase:
        def __init__(self) -> None:
            self.request: object | None = None

        def execute(self, req: object) -> dict[str, str]:
            self.request = req
            return {"status": "ok", "manifest_id": "abc"}

    class StubContainer:
        def __init__(self) -> None:
            self.uc = StubUseCase()

        def replay_manifest_uc(self) -> StubUseCase:
            return self.uc

    container = StubContainer()
    monkeypatch.setattr(Container, "get", lambda: container)

    result = tools.replay_manifest(manifest_id="abc", output_dir="out")

    assert result["status"] == "ok"
    assert isinstance(container.uc.request, ReplayManifestRequest)
    assert container.uc.request.manifest_id == "abc"
    assert container.uc.request.output_dir == "out"


def test_retarget_journal_passes_request(monkeypatch: MonkeyPatch) -> None:
    class StubUseCase:
        def __init__(self) -> None:
            self.request: object | None = None

        def execute(self, req: object) -> dict[str, str]:
            self.request = req
            return {"status": "ok", "manifest_id": "xyz"}

    class StubContainer:
        def __init__(self) -> None:
            self.uc = StubUseCase()

        def retarget_journal_uc(self) -> StubUseCase:
            return self.uc

    container = StubContainer()
    monkeypatch.setattr(Container, "get", lambda: container)

    result = tools.retarget_journal(manifest_id="xyz", target_journal="Nature")

    assert result["status"] == "ok"
    assert isinstance(container.uc.request, RetargetJournalRequest)
    assert container.uc.request.manifest_id == "xyz"
    assert container.uc.request.target_journal == "Nature"


def test_list_manifests_validates_limit(monkeypatch: MonkeyPatch) -> None:
    class StubUseCase:
        def execute(self, req: object) -> dict[str, str]:
            assert isinstance(req, ListManifestsRequest)
            return {"status": "ok"}

    class StubContainer:
        def list_manifests_uc(self) -> StubUseCase:
            return StubUseCase()

    monkeypatch.setattr(Container, "get", lambda: StubContainer())

    result = tools.list_manifests(limit=5)

    assert result["status"] == "ok"
