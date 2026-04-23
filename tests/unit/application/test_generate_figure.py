from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, cast

import pytest
from PIL import Image

from src.application.generate_figure import GenerateFigureRequest, GenerateFigureUseCase
from src.domain.entities import GenerationManifest, GenerationResult, GenerationResultStatus, Paper
from src.domain.exceptions import ValidationError
from src.domain.interfaces import (
    ImageGenerator,
    ImageVerifier,
    ManifestStore,
    MetadataFetcher,
    PromptBuilder,
)
from src.domain.value_objects import QualityVerdict
from src.infrastructure.output_formatter import PillowOutputFormatter


class FailFetcher(MetadataFetcher):
    def fetch_paper(self, pmid: str) -> Paper:
        raise AssertionError(f"fetch_paper should not run for planned payloads: {pmid}")


class StubFetcher(MetadataFetcher):
    def fetch_paper(self, pmid: str) -> Paper:
        return Paper(
            pmid=pmid,
            title="Academic workflow dashboard",
            authors="Example Author",
            journal="Journal of Testing",
            abstract="Overview infographic for academic workflow orchestration.",
        )


class StubGenerator(ImageGenerator):
    def __init__(self) -> None:
        self.prompt = ""
        self.generate_kwargs: dict[str, object] = {}

    def generate(self, prompt: str, **kwargs: object) -> GenerationResult:
        self.prompt = prompt
        self.generate_kwargs = kwargs
        return GenerationResult(image_bytes=b"fake-png", model="stub-model")

    def edit(self, image_path: Path, instruction: str, **_: object) -> GenerationResult:
        raise AssertionError(f"edit should not run: {image_path} {instruction}")


class StubPromptBuilder(PromptBuilder):
    def __init__(self) -> None:
        self.inject_target_journal: str | None = None
        self.build_calls = 0
        self.inject_calls = 0

    def build_prompt(
        self,
        paper: Paper,
        figure_type: str,
        language: str,
        output_size: str,
        expected_labels: list[str] | None = None,
    ) -> str:
        self.build_calls += 1
        raise AssertionError(
            "build_prompt should not run for planned payloads: "
            f"{paper} {figure_type} {language} {output_size}"
        )

    def inject_journal_requirements(
        self,
        prompt: str,
        *,
        target_journal: str | None = None,
        source_journal: str | None = None,
    ) -> tuple[str, dict[str, object] | None]:
        self.inject_calls += 1
        self.inject_target_journal = target_journal
        if target_journal == "Nature":
            return (
                prompt + "\n\n## Journal Profile\nprofile: Nature Portfolio",
                {
                    "id": "nature_portfolio",
                    "display_name": "Nature Portfolio",
                    "matched_by": "target_journal",
                },
            )
        return prompt, None


class StubManifestStore(ManifestStore):
    def __init__(self) -> None:
        self.saved: list[GenerationManifest] = []

    def save(self, manifest: GenerationManifest) -> GenerationManifest:
        self.saved.append(manifest)
        return manifest

    def load(self, manifest_id: str) -> GenerationManifest:
        raise AssertionError(f"load should not be called for {manifest_id}")

    def list(self, limit: int = 20) -> list[GenerationManifest]:
        return self.saved[:limit]


class StubComposer:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.calls: list[dict[str, object]] = []

    def compose(
        self,
        panels: list[dict[str, str]],
        *,
        title: str,
        caption: str,
        citation: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        self.calls.append(
            {"panels": panels, "title": title, "caption": caption, "citation": citation}
        )
        out_path = Path(output_path or (self.output_dir / "composite.png"))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(_png_bytes())
        return {
            "status": "success",
            "output_path": str(out_path),
        }


class StubVerifier(ImageVerifier):
    def __init__(self, verdict: QualityVerdict) -> None:
        self.verdict = verdict
        self.calls: list[dict[str, object]] = []

    def verify(
        self,
        image_bytes: bytes,
        *,
        expected_labels: list[str],
        figure_type: str,
        language: str,
    ) -> QualityVerdict:
        self.calls.append(
            {
                "image_bytes": image_bytes,
                "expected_labels": expected_labels,
                "figure_type": figure_type,
                "language": language,
            }
        )
        return self.verdict


class BridgePromptBuilder(PromptBuilder):
    def __init__(self) -> None:
        self.build_calls = 0
        self.inject_calls = 0

    def build_prompt(
        self,
        paper: Paper,
        figure_type: str,
        language: str,
        output_size: str,
        expected_labels: list[str] | None = None,
    ) -> str:
        self.build_calls += 1
        source_marker = paper.pmid or paper.source_identifier or paper.title
        return f"planned::{source_marker}::{figure_type}::{language}::{output_size}"

    def inject_journal_requirements(
        self,
        prompt: str,
        *,
        target_journal: str | None = None,
        source_journal: str | None = None,
    ) -> tuple[str, dict[str, object] | None]:
        self.inject_calls += 1
        if target_journal == "Nature":
            return (
                prompt + "::nature",
                {
                    "id": "nature_portfolio",
                    "display_name": "Nature Portfolio",
                    "matched_by": "target_journal",
                },
            )
        return prompt, None


class StubPlanner:
    def __init__(self, planned_payload: dict[str, object]) -> None:
        self._planned_payload = planned_payload
        self.calls: list[GenerateFigureRequest | object] = []

    def execute(self, request: object) -> dict[str, object]:
        self.calls.append(request)
        return {
            "status": "ok",
            "planned_payload": self._planned_payload,
            "pmid": "99999999",
            "selected_figure_type": self._planned_payload.get(
                "selected_figure_type",
                "infographic",
            ),
            "warnings": ["planner warning"],
        }


def _png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", (2, 2), (20, 120, 200, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_generate_figure_supports_generic_planned_payload(tmp_path: Path) -> None:
    generator = StubGenerator()
    prompt_builder = StubPromptBuilder()
    use_case = GenerateFigureUseCase(
        fetcher=FailFetcher(),
        generator=generator,
        prompt_builder=prompt_builder,
        output_dir=str(tmp_path),
        output_formatter=PillowOutputFormatter(),
    )

    payload = {
        "asset_kind": "repo_icon",
        "title": "Academic Figures MCP",
        "goal": "Create a distinctive icon for the Academic Figures MCP repository.",
        "selected_figure_type": "infographic",
        "render_route": "image_generation",
        "language": "en",
        "output_size": "1024x1024",
        "target_journal": "Nature",
        "source_context": {
            "repo": "academic-figures-mcp",
            "tagline": "workflow-first academic figure harness",
        },
        "must_include": [
            "scientific paper silhouette",
            "diagram nodes or chart motif",
            "strong teal and amber contrast",
        ],
    }

    result = use_case.execute(
        GenerateFigureRequest(planned_payload=payload, output_dir=str(tmp_path))
    )

    assert result["status"] == "ok"
    assert result["result_status"] == GenerationResultStatus.IMAGE_READY.value
    assert result["error_kind"] is None
    assert result["asset_kind"] == "repo_icon"
    assert result["render_route_used"] == "image_generation"
    assert Path(str(result["output_path"])).exists()
    assert "repo_icon" in generator.prompt
    assert generator.generate_kwargs["output_size"] == "1024x1024"
    assert "## Journal Profile" in generator.prompt
    journal_profile = cast("dict[str, object]", result["journal_profile"])
    assert journal_profile["id"] == "nature_portfolio"
    assert prompt_builder.inject_target_journal == "Nature"
    assert result["generation_contract"] == "planned_payload"


def test_generate_figure_rejects_unsupported_render_route_payload(tmp_path: Path) -> None:
    generator = StubGenerator()
    prompt_builder = StubPromptBuilder()
    use_case = GenerateFigureUseCase(
        fetcher=FailFetcher(),
        generator=generator,
        prompt_builder=prompt_builder,
        output_dir=str(tmp_path),
        output_formatter=PillowOutputFormatter(),
    )

    payload = {
        "asset_kind": "academic_figure",
        "title": "Deterministic Flowchart",
        "selected_figure_type": "flowchart",
        "render_route": "code_render_svg",
    }

    result = use_case.execute(
        GenerateFigureRequest(planned_payload=payload, output_dir=str(tmp_path))
    )

    assert result["status"] == "unsupported_render_route"
    assert result["error_status"] == "unsupported_render_route"
    assert result["error_category"] == "unsupported"
    assert "result_status" not in result
    assert result["render_route_requested"] == "code_render_svg"
    assert result["supported_render_routes"] == [
        "image_generation",
        "composite_figure",
        "layout_assemble_composite",
    ]
    assert "not executable" in str(result["error"])
    assert generator.prompt == ""
    assert prompt_builder.inject_calls == 0


def test_generate_figure_pmid_single_entry_runs_internal_plan_first(tmp_path: Path) -> None:
    generator = StubGenerator()
    prompt_builder = BridgePromptBuilder()
    use_case = GenerateFigureUseCase(
        fetcher=StubFetcher(),
        generator=generator,
        prompt_builder=prompt_builder,
        output_dir=str(tmp_path),
        output_formatter=PillowOutputFormatter(),
    )

    result = use_case.execute(
        GenerateFigureRequest(
            pmid="12345678",
            figure_type="infographic",
            target_journal="Nature",
            output_dir=str(tmp_path),
        )
    )

    assert result["status"] == "ok"
    assert result["generation_contract"] == "single_entry_plan_first"
    assert result["pmid"] == "12345678"
    assert result["figure_type"] == "infographic"
    assert Path(str(result["output_path"])).exists()
    assert generator.prompt == "planned::12345678::infographic::zh-TW::1024x1536::nature"
    assert prompt_builder.build_calls == 1
    assert prompt_builder.inject_calls == 1


def test_generate_figure_uses_injected_planner_for_plan_first_bridge(tmp_path: Path) -> None:
    generator = StubGenerator()
    prompt_builder = StubPromptBuilder()
    planner = StubPlanner(
        {
            "asset_kind": "academic_figure",
            "title": "Injected Planner",
            "selected_figure_type": "infographic",
            "render_route": "image_generation",
            "language": "en",
            "output_size": "1024x1024",
            "goal": "Render using injected planner output.",
        }
    )
    use_case = GenerateFigureUseCase(
        fetcher=FailFetcher(),
        generator=generator,
        prompt_builder=prompt_builder,
        planner=planner,
        output_dir=str(tmp_path),
        output_formatter=PillowOutputFormatter(),
    )

    result = use_case.execute(
        GenerateFigureRequest(
            pmid="12345678",
            figure_type="infographic",
            output_dir=str(tmp_path),
        )
    )

    assert result["status"] == "ok"
    assert result["generation_contract"] == "single_entry_plan_first"
    assert result["pmid"] == "99999999"
    assert planner.calls
    assert generator.prompt != ""
    assert prompt_builder.build_calls == 0


def test_generate_figure_generic_source_single_entry_runs_internal_plan_first(
    tmp_path: Path,
) -> None:
    generator = StubGenerator()
    prompt_builder = BridgePromptBuilder()
    use_case = GenerateFigureUseCase(
        fetcher=StubFetcher(),
        generator=generator,
        prompt_builder=prompt_builder,
        output_dir=str(tmp_path),
        output_formatter=PillowOutputFormatter(),
    )

    result = use_case.execute(
        GenerateFigureRequest(
            source_title="HyperHierarchicalRAG repository overview",
            source_summary="Explain the retrieval hierarchy and orchestrator flow.",
            source_kind="repo",
            source_identifier="github.com/example/hhrag",
            figure_type="infographic",
            output_dir=str(tmp_path),
        )
    )

    assert result["status"] == "ok"
    assert result["generation_contract"] == "single_entry_plan_first"
    assert result["pmid"] is None
    assert result["source_kind"] == "repo"
    assert result["source_identifier"] == "github.com/example/hhrag"
    assert Path(str(result["output_path"])).exists()
    assert generator.prompt == "planned::github.com/example/hhrag::infographic::zh-TW::1024x1536"
    assert prompt_builder.build_calls == 1
    assert prompt_builder.inject_calls == 1


def test_generate_figure_persists_manifest(tmp_path: Path) -> None:
    generator = StubGenerator()
    prompt_builder = StubPromptBuilder()
    manifest_store = StubManifestStore()
    use_case = GenerateFigureUseCase(
        fetcher=FailFetcher(),
        generator=generator,
        prompt_builder=prompt_builder,
        output_dir=str(tmp_path),
        manifest_store=manifest_store,
        output_formatter=PillowOutputFormatter(),
    )

    payload = {
        "asset_kind": "repo_icon",
        "title": "Academic Figures MCP",
        "goal": "Create a distinctive icon for the Academic Figures MCP repository.",
        "selected_figure_type": "infographic",
        "render_route": "image_generation",
        "language": "en",
        "output_size": "1024x1024",
        "target_journal": "Nature",
        "source_context": {
            "repo": "academic-figures-mcp",
            "tagline": "workflow-first academic figure harness",
        },
        "must_include": [
            "scientific paper silhouette",
            "diagram nodes or chart motif",
            "strong teal and amber contrast",
        ],
    }

    result = use_case.execute(
        GenerateFigureRequest(planned_payload=payload, output_dir=str(tmp_path))
    )

    assert result["manifest_id"] is not None
    assert manifest_store.saved
    manifest = manifest_store.saved[0]
    assert manifest.asset_kind == "repo_icon"
    assert manifest.prompt.startswith("## Block 1")
    assert manifest.prompt_base.startswith("## Block 1")
    assert manifest.render_route_used == "image_generation"
    assert manifest.review_summary is not None
    assert manifest.review_summary["policy"] == "provider_vision_required_host_optional"
    assert manifest.review_history == []


def test_generate_figure_handles_composite_render_route(tmp_path: Path) -> None:
    generator = StubGenerator()
    prompt_builder = StubPromptBuilder()
    manifest_store = StubManifestStore()
    composer = StubComposer(tmp_path)
    use_case = GenerateFigureUseCase(
        fetcher=FailFetcher(),
        generator=generator,
        prompt_builder=prompt_builder,
        output_dir=str(tmp_path),
        manifest_store=manifest_store,
        composer=composer,
        output_formatter=PillowOutputFormatter(),
    )

    payload = {
        "asset_kind": "academic_figure",
        "title": "Composite Assembly",
        "selected_figure_type": "infographic",
        "render_route": "composite_figure",
        "panels": [
            {"image_path": str(tmp_path / "panel-a.png"), "label": "A", "panel_type": "chart"},
            {"image_path": str(tmp_path / "panel-b.png"), "label": "B", "panel_type": "anatomy"},
        ],
    }

    result = use_case.execute(
        GenerateFigureRequest(planned_payload=payload, output_dir=str(tmp_path))
    )

    assert result["status"] == "ok"
    assert result["render_route_used"] == "composite_figure"
    assert composer.calls
    assert manifest_store.saved
    assert generator.prompt == ""


def test_generate_figure_returns_quality_gate_for_image_generation(tmp_path: Path) -> None:
    generator = StubGenerator()
    prompt_builder = StubPromptBuilder()
    manifest_store = StubManifestStore()
    verifier = StubVerifier(
        QualityVerdict(
            passed=False,
            domain_scores={"text_accuracy": 2.0, "layout": 4.0},
            total_score=26.0,
            critical_issues=("Text label mismatch",),
            text_verification_passed=False,
            missing_labels=("Acute MI",),
            summary="Label fidelity is insufficient.",
        )
    )
    use_case = GenerateFigureUseCase(
        fetcher=FailFetcher(),
        generator=generator,
        prompt_builder=prompt_builder,
        output_dir=str(tmp_path),
        manifest_store=manifest_store,
        verifier=verifier,
        output_formatter=PillowOutputFormatter(),
    )

    payload = {
        "asset_kind": "repo_icon",
        "title": "Academic Figures MCP",
        "goal": "Create a distinctive icon for the Academic Figures MCP repository.",
        "selected_figure_type": "infographic",
        "render_route": "image_generation",
        "language": "zh-TW",
        "expected_labels": ["Acute MI"],
        "source_context": {"repo": "academic-figures-mcp"},
    }

    result = use_case.execute(
        GenerateFigureRequest(planned_payload=payload, output_dir=str(tmp_path))
    )

    quality_gate = cast("dict[str, object]", result["quality_gate"])
    review_summary = cast("dict[str, Any]", result["review_summary"])
    warnings = cast("list[str]", result["warnings"])
    assert quality_gate["passed"] is False
    assert quality_gate["route_status"] == "executed"
    assert quality_gate["review_status"] == "failed"
    assert quality_gate["missing_labels"] == ["Acute MI"]
    assert review_summary["provider_baseline_met"] is False
    assert review_summary["requirement_met"] is False
    assert review_summary["routes"]["host_vision"]["status"] == "external"
    assert review_summary["recommended_next_action"] == "fix_and_rerun_provider_review"
    review_history = cast("list[dict[str, object]]", result["review_history"])
    assert review_history[0]["route"] == "provider_vision"
    assert review_history[0]["route_status"] == "recorded"
    assert manifest_store.saved[0].review_history[0]["route"] == "provider_vision"
    assert verifier.calls[0]["expected_labels"] == ["Acute MI"]
    assert "Quality gate FAILED" in warnings[0]
    assert "Missing/garbled labels: Acute MI" in warnings[1]


def test_generate_figure_returns_quality_gate_for_composite_route(tmp_path: Path) -> None:
    generator = StubGenerator()
    prompt_builder = StubPromptBuilder()
    manifest_store = StubManifestStore()
    composer = StubComposer(tmp_path)
    verifier = StubVerifier(
        QualityVerdict(
            passed=True,
            domain_scores={"layout": 4.0, "visual_polish": 4.0},
            total_score=32.0,
            critical_issues=(),
            text_verification_passed=True,
            missing_labels=(),
            summary="Composite passed the gate.",
        )
    )
    use_case = GenerateFigureUseCase(
        fetcher=FailFetcher(),
        generator=generator,
        prompt_builder=prompt_builder,
        output_dir=str(tmp_path),
        manifest_store=manifest_store,
        composer=composer,
        verifier=verifier,
        output_formatter=PillowOutputFormatter(),
    )

    payload = {
        "asset_kind": "academic_figure",
        "title": "Composite Assembly",
        "selected_figure_type": "infographic",
        "render_route": "composite_figure",
        "expected_labels": ["Panel A", "Panel B"],
        "panels": [
            {"image_path": str(tmp_path / "panel-a.png"), "label": "A", "panel_type": "chart"},
            {"image_path": str(tmp_path / "panel-b.png"), "label": "B", "panel_type": "anatomy"},
        ],
    }

    result = use_case.execute(
        GenerateFigureRequest(planned_payload=payload, output_dir=str(tmp_path))
    )

    quality_gate = cast("dict[str, object]", result["quality_gate"])
    review_summary = cast("dict[str, Any]", result["review_summary"])
    assert result["status"] == "ok"
    assert result["render_route_used"] == "composite_figure"
    assert quality_gate["passed"] is True
    assert quality_gate["route_status"] == "executed"
    assert quality_gate["review_status"] == "passed"
    assert review_summary["provider_baseline_met"] is True
    assert review_summary["requirement_met"] is True
    assert verifier.calls[0]["expected_labels"] == ["Panel A", "Panel B"]


def test_generate_figure_converts_requested_output_format(tmp_path: Path) -> None:
    class ConvertingGenerator(StubGenerator):
        def generate(self, prompt: str, **_: object) -> GenerationResult:
            self.prompt = prompt
            return GenerationResult(
                image_bytes=_png_bytes(),
                media_type="image/png",
                model="stub-model",
            )

    generator = ConvertingGenerator()
    prompt_builder = StubPromptBuilder()
    use_case = GenerateFigureUseCase(
        fetcher=FailFetcher(),
        generator=generator,
        prompt_builder=prompt_builder,
        output_dir=str(tmp_path),
        output_formatter=PillowOutputFormatter(),
    )

    payload = {
        "asset_kind": "repo_icon",
        "title": "Academic Figures MCP",
        "goal": "Create a distinctive icon for the Academic Figures MCP repository.",
        "selected_figure_type": "infographic",
        "render_route": "image_generation",
        "language": "en",
        "output_size": "1024x1024",
        "source_context": {"repo": "academic-figures-mcp"},
    }

    result = use_case.execute(
        GenerateFigureRequest(
            planned_payload=payload,
            output_format="jpeg",
            output_dir=str(tmp_path),
        )
    )

    output_path = Path(str(result["output_path"]))
    assert result["status"] == "ok"
    assert result["output_format"] == "jpeg"
    assert result["media_type"] == "image/jpeg"
    assert output_path.suffix == ".jpg"
    assert output_path.read_bytes().startswith(b"\xff\xd8\xff")


def test_generate_figure_converts_requested_output_format_to_gif(tmp_path: Path) -> None:
    class ConvertingGenerator(StubGenerator):
        def generate(self, prompt: str, **_: object) -> GenerationResult:
            self.prompt = prompt
            return GenerationResult(
                image_bytes=_png_bytes(),
                media_type="image/png",
                model="stub-model",
            )

    generator = ConvertingGenerator()
    prompt_builder = StubPromptBuilder()
    use_case = GenerateFigureUseCase(
        fetcher=FailFetcher(),
        generator=generator,
        prompt_builder=prompt_builder,
        output_dir=str(tmp_path),
        output_formatter=PillowOutputFormatter(),
    )

    payload = {
        "asset_kind": "repo_icon",
        "title": "Academic Figures MCP",
        "goal": "Create a distinctive icon for the Academic Figures MCP repository.",
        "selected_figure_type": "infographic",
        "render_route": "image_generation",
        "language": "en",
        "output_size": "1024x1024",
        "source_context": {"repo": "academic-figures-mcp"},
    }

    result = use_case.execute(
        GenerateFigureRequest(
            planned_payload=payload,
            output_format="gif",
            output_dir=str(tmp_path),
        )
    )

    output_path = Path(str(result["output_path"]))
    assert result["status"] == "ok"
    assert result["output_format"] == "gif"
    assert result["media_type"] == "image/gif"
    assert output_path.suffix == ".gif"
    assert output_path.read_bytes().startswith(b"GIF8")


def test_generate_request_rejects_conflicting_source_modes() -> None:
    with pytest.raises(ValidationError, match="Provide either planned_payload or source inputs"):
        GenerateFigureRequest(planned_payload={"goal": "x"}, pmid="12345678")

    with pytest.raises(ValidationError, match="Provide either pmid or source_title, not both"):
        GenerateFigureRequest(pmid="12345678", source_title="Repo brief")


def test_generate_figure_composite_manifest_uses_final_output_path(tmp_path: Path) -> None:
    generator = StubGenerator()
    prompt_builder = StubPromptBuilder()
    manifest_store = StubManifestStore()
    composer = StubComposer(tmp_path)
    use_case = GenerateFigureUseCase(
        fetcher=FailFetcher(),
        generator=generator,
        prompt_builder=prompt_builder,
        output_dir=str(tmp_path),
        manifest_store=manifest_store,
        composer=composer,
        output_formatter=PillowOutputFormatter(),
    )

    payload = {
        "asset_kind": "academic_figure",
        "title": "Composite Assembly",
        "selected_figure_type": "infographic",
        "render_route": "composite_figure",
        "panels": [
            {"image_path": str(tmp_path / "panel-a.png"), "label": "A", "panel_type": "chart"},
            {"image_path": str(tmp_path / "panel-b.png"), "label": "B", "panel_type": "anatomy"},
        ],
    }

    result = use_case.execute(
        GenerateFigureRequest(
            planned_payload=payload,
            output_format="jpeg",
            output_dir=str(tmp_path),
        )
    )

    manifest = manifest_store.saved[0]
    assert result["status"] == "ok"
    assert str(manifest.output_path).endswith(".jpg")
    assert manifest.output_path == result["output_path"]
