from __future__ import annotations

from typing import TYPE_CHECKING, cast

from src.application.get_manifest_detail import GetManifestDetailRequest
from src.application.list_manifests import ListManifestsRequest
from src.application.record_host_review import RecordHostReviewRequest
from src.application.replay_manifest import ReplayManifestRequest
from src.application.retarget_journal import RetargetJournalRequest
from src.presentation import tools
from src.presentation.dependencies import Container

if TYPE_CHECKING:
    from pytest import MonkeyPatch

    from src.application.composite_figure import CompositeFigureRequest
    from src.application.generate_figure import GenerateFigureRequest
    from src.application.plan_figure import PlanFigureRequest
    from src.application.prepare_publication_image import PreparePublicationImageRequest


def test_generate_figure_rejects_invalid_pmid(monkeypatch: MonkeyPatch) -> None:
    def fail_container_get() -> object:
        raise AssertionError("container should not run")

    monkeypatch.setattr(Container, "get", fail_container_get)

    result = tools.generate_figure(pmid="pmid-abc")

    assert result["status"] == "error"
    assert result["error_status"] == "error"
    assert result["error_category"] == "validation"
    assert "digits" in str(result["error"])


def test_plan_figure_rejects_invalid_output_size(monkeypatch: MonkeyPatch) -> None:
    def fail_container_get() -> object:
        raise AssertionError("container should not run")

    monkeypatch.setattr(Container, "get", fail_container_get)

    result = tools.plan_figure(pmid="12345678", output_size="huge")

    assert result["status"] == "error"
    assert result["error_status"] == "error"
    assert result["error_category"] == "validation"
    assert "output_size" in str(result["error"])


def test_plan_figure_accepts_generic_source(monkeypatch: MonkeyPatch) -> None:
    class StubUseCase:
        def __init__(self) -> None:
            self.request: object | None = None

        def execute(self, req: object) -> dict[str, str]:
            self.request = req
            return {"status": "ok"}

    class StubContainer:
        def __init__(self) -> None:
            self.plan_use_case = StubUseCase()

        def plan_figure_uc(self) -> StubUseCase:
            return self.plan_use_case

    container = StubContainer()
    monkeypatch.setattr(Container, "get", lambda: container)

    result = tools.plan_figure(
        source_title="Academic Figures MCP repo",
        source_summary="Tooling for planning and generating publication-ready visuals.",
        source_kind="repo",
        source_identifier="github.com/u9401066/academic-figures-mcp",
        output_format="webp",
    )

    assert result["status"] == "ok"
    request = cast("PlanFigureRequest", container.plan_use_case.request)
    assert request is not None
    assert request.pmid is None
    assert request.source_title == "Academic Figures MCP repo"
    assert request.source_kind == "repo"
    assert request.source_identifier == "github.com/u9401066/academic-figures-mcp"
    assert request.output_format == "webp"


def test_plan_figure_rejects_mixed_pmid_and_generic_source(monkeypatch: MonkeyPatch) -> None:
    def fail_container_get() -> object:
        raise AssertionError("container should not run")

    monkeypatch.setattr(Container, "get", fail_container_get)

    result = tools.plan_figure(
        pmid="12345678",
        source_title="Conflicting source",
    )

    assert result["status"] == "error"
    assert result["error_status"] == "error"
    assert result["error_category"] == "validation"
    assert "either pmid or source_title" in str(result["error"])


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
        output_format="jpeg",
        output_dir="brand-output",
        target_journal="Nature",
    )

    assert result["status"] == "ok"
    request = cast("GenerateFigureRequest", container.generate_use_case.request)
    assert request is not None
    assert request.pmid is None
    assert request.planned_payload == payload
    assert request.output_format == "jpeg"
    assert request.output_dir == "brand-output"
    assert request.target_journal == "Nature"


def test_generate_figure_accepts_generic_source(monkeypatch: MonkeyPatch) -> None:
    class StubGenerateUseCase:
        def __init__(self) -> None:
            self.request: object | None = None

        def execute(self, req: object) -> dict[str, str]:
            self.request = req
            return {"status": "ok", "asset_kind": "repository_figure"}

    class StubContainer:
        def __init__(self) -> None:
            self.generate_use_case = StubGenerateUseCase()

        def generate_figure_uc(self) -> StubGenerateUseCase:
            return self.generate_use_case

    container = StubContainer()
    monkeypatch.setattr(Container, "get", lambda: container)

    result = tools.generate_figure(
        source_title="Academic Figures MCP repo",
        source_summary="Tooling for planning and generating publication-ready visuals.",
        source_kind="repo",
        source_identifier="github.com/u9401066/academic-figures-mcp",
        output_format="webp",
    )

    assert result["status"] == "ok"
    request = cast("GenerateFigureRequest", container.generate_use_case.request)
    assert request is not None
    assert request.pmid is None
    assert request.source_title == "Academic Figures MCP repo"
    assert request.source_kind == "repo"
    assert request.source_identifier == "github.com/u9401066/academic-figures-mcp"
    assert request.output_format == "webp"


def test_composite_figure_rejects_mismatched_labels() -> None:
    result = tools.composite_figure(
        panels=[["panel-a.png", "anatomy"]],
        labels=["A", "B"],
        title="Composite",
    )

    assert result["status"] == "error"
    assert result["error_status"] == "error"
    assert result["error_category"] == "validation"
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


def test_prepare_publication_image_passes_request(monkeypatch: MonkeyPatch) -> None:
    class StubUseCase:
        def __init__(self) -> None:
            self.request: object | None = None

        def execute(self, req: object) -> dict[str, object]:
            self.request = req
            return {"status": "ok", "generation_used": False}

    class StubContainer:
        def __init__(self) -> None:
            self.uc = StubUseCase()

        def prepare_publication_image_uc(self) -> StubUseCase:
            return self.uc

    container = StubContainer()
    monkeypatch.setattr(Container, "get", lambda: container)

    result = tools.prepare_publication_image(
        image_path=" figure.png ",
        output_path=" prepared.tif ",
        target_dpi=600,
        width_mm=60.0,
        output_format="tif",
        allow_upscale=False,
    )

    assert result["status"] == "ok"
    request = cast("PreparePublicationImageRequest", container.uc.request)
    assert request is not None
    assert request.image_path == "figure.png"
    assert request.output_path == "prepared.tif"
    assert request.target_dpi == 600
    assert request.width_mm == 60.0
    assert request.height_mm is None
    assert request.output_format == "tiff"
    assert request.allow_upscale is False


def test_prepare_publication_image_rejects_invalid_dpi(monkeypatch: MonkeyPatch) -> None:
    def fail_container_get() -> object:
        raise AssertionError("container should not run")

    monkeypatch.setattr(Container, "get", fail_container_get)

    result = tools.prepare_publication_image(image_path="figure.png", target_dpi=10)

    assert result["status"] == "error"
    assert result["error_status"] == "error"
    assert result["error_category"] == "validation"
    assert "target_dpi" in str(result["error"])


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


def test_record_host_review_passes_request(monkeypatch: MonkeyPatch) -> None:
    class StubUseCase:
        def __init__(self) -> None:
            self.request: object | None = None

        def execute(self, req: object) -> dict[str, str]:
            self.request = req
            return {"status": "ok", "manifest_id": "xyz"}

    class StubContainer:
        def __init__(self) -> None:
            self.uc = StubUseCase()

        def record_host_review_uc(self) -> StubUseCase:
            return self.uc

    container = StubContainer()
    monkeypatch.setattr(Container, "get", lambda: container)

    result = tools.record_host_review(
        manifest_id="xyz",
        passed=True,
        summary="Copilot visual review passed.",
        critical_issues=[""],
    )

    assert result["status"] == "ok"
    assert isinstance(container.uc.request, RecordHostReviewRequest)
    assert container.uc.request.manifest_id == "xyz"
    assert container.uc.request.passed is True
    assert container.uc.request.summary == "Copilot visual review passed."


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


def test_get_manifest_detail_passes_request(monkeypatch: MonkeyPatch) -> None:
    class StubUseCase:
        def __init__(self) -> None:
            self.request: object | None = None

        def execute(self, req: object) -> dict[str, str]:
            self.request = req
            return {"status": "ok", "manifest_id": "xyz"}

    class StubContainer:
        def __init__(self) -> None:
            self.uc = StubUseCase()

        def get_manifest_detail_uc(self) -> StubUseCase:
            return self.uc

    container = StubContainer()
    monkeypatch.setattr(Container, "get", lambda: container)

    result = tools.get_manifest_detail(manifest_id="xyz", include_lineage=False)

    assert result["status"] == "ok"
    assert isinstance(container.uc.request, GetManifestDetailRequest)
    assert container.uc.request.manifest_id == "xyz"
    assert container.uc.request.include_lineage is False
