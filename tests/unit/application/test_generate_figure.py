from __future__ import annotations

from pathlib import Path
from typing import cast

from src.application.generate_figure import GenerateFigureRequest, GenerateFigureUseCase
from src.domain.entities import GenerationManifest, GenerationResult, Paper
from src.domain.interfaces import ImageGenerator, ManifestStore, MetadataFetcher, PromptBuilder


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

    def generate(self, prompt: str, **_: object) -> GenerationResult:
        self.prompt = prompt
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
        out_path.write_bytes(b"composite")
        return {
            "status": "success",
            "output_path": str(out_path),
        }


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
        return f"planned::{paper.pmid}::{figure_type}::{language}::{output_size}"

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


def test_generate_figure_supports_generic_planned_payload(tmp_path: Path) -> None:
    generator = StubGenerator()
    prompt_builder = StubPromptBuilder()
    use_case = GenerateFigureUseCase(
        fetcher=FailFetcher(),
        generator=generator,
        prompt_builder=prompt_builder,
        output_dir=str(tmp_path),
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
    assert result["asset_kind"] == "repo_icon"
    assert result["render_route_used"] == "image_generation"
    assert Path(str(result["output_path"])).exists()
    assert "repo_icon" in generator.prompt
    assert "## Journal Profile" in generator.prompt
    journal_profile = cast("dict[str, object]", result["journal_profile"])
    assert journal_profile["id"] == "nature_portfolio"
    assert prompt_builder.inject_target_journal == "Nature"
    assert result["generation_contract"] == "planned_payload"


def test_generate_figure_pmid_bridge_runs_internal_plan_first(tmp_path: Path) -> None:
    generator = StubGenerator()
    prompt_builder = BridgePromptBuilder()
    use_case = GenerateFigureUseCase(
        fetcher=StubFetcher(),
        generator=generator,
        prompt_builder=prompt_builder,
        output_dir=str(tmp_path),
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
    assert result["generation_contract"] == "pmid_compatibility_bridge"
    assert result["pmid"] == "12345678"
    assert result["figure_type"] == "infographic"
    assert Path(str(result["output_path"])).exists()
    assert generator.prompt == "planned::12345678::infographic::zh-TW::1024x1536::nature"
    assert prompt_builder.build_calls == 1
    assert prompt_builder.inject_calls == 1
    warnings = cast("list[str]", result["warnings"])
    assert any("plan-first compatibility bridge" in warning for warning in warnings)


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
