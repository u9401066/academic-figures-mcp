from __future__ import annotations

from pathlib import Path
from typing import Any

from src.application.list_manifests import ListManifestsRequest, ListManifestsUseCase
from src.application.replay_manifest import ReplayManifestRequest, ReplayManifestUseCase
from src.application.retarget_journal import RetargetJournalRequest, RetargetJournalUseCase
from src.domain.entities import GenerationManifest, GenerationResult
from src.domain.interfaces import ImageGenerator, ManifestStore, PromptBuilder


class StubGenerator(ImageGenerator):
    def __init__(self) -> None:
        self.prompt = ""

    def generate(self, prompt: str, **_: object) -> GenerationResult:
        self.prompt = prompt
        return GenerationResult(image_bytes=b"fake", model="stub-model")

    def edit(self, image_path: Path, instruction: str, **_: object) -> GenerationResult:
        raise AssertionError(f"edit should not run: {image_path} {instruction}")


class StubPromptBuilder(PromptBuilder):
    def __init__(self) -> None:
        self.inject_target: str | None = None

    def build_prompt(
        self,
        paper: Any,
        figure_type: str,
        language: str,
        output_size: str,
        expected_labels: list[str] | None = None,
    ) -> str:
        raise AssertionError("build_prompt should not run in retarget tests")

    def inject_journal_requirements(
        self,
        prompt: str,
        *,
        target_journal: str | None = None,
        source_journal: str | None = None,
    ) -> tuple[str, dict[str, object] | None]:
        self.inject_target = target_journal
        if target_journal:
            return (
                f"{prompt}::{target_journal}",
                {"id": target_journal.lower(), "matched_by": "target_journal"},
            )
        return (prompt, None)


class StubManifestStore(ManifestStore):
    def __init__(self, manifest: GenerationManifest) -> None:
        self.manifest = manifest
        self.saved: list[GenerationManifest] = []

    def save(self, manifest: GenerationManifest) -> GenerationManifest:
        self.saved.append(manifest)
        return manifest

    def load(self, manifest_id: str) -> GenerationManifest:
        assert manifest_id == self.manifest.manifest_id
        return self.manifest

    def list(self, limit: int = 20) -> list[GenerationManifest]:
        manifests = [self.manifest, *self.saved]
        return manifests[:limit]


def _base_manifest(output_path: Path) -> GenerationManifest:
    return GenerationManifest(
        manifest_id="manifest-1",
        asset_kind="academic_figure",
        figure_type="infographic",
        language="en",
        output_size="1024x1536",
        render_route_requested="image_generation",
        render_route_used="image_generation",
        prompt="prompt::with-journal",
        prompt_base="prompt::base",
        planned_payload={"asset_kind": "academic_figure"},
        target_journal="Nature",
        journal_profile={"id": "nature_portfolio"},
        source_context={"pmid": "123", "journal": "Nature Medicine"},
        output_path=str(output_path),
        model="stub-model",
        provider="google",
        generation_contract="planned_payload",
        warnings=["baseline-warning"],
    )


def test_replay_manifest_reuses_prompt(tmp_path: Path) -> None:
    base_manifest = _base_manifest(tmp_path / "orig.png")
    store = StubManifestStore(base_manifest)
    generator = StubGenerator()
    uc = ReplayManifestUseCase(
        manifest_store=store,
        generator=generator,
        default_output_dir=str(tmp_path),
    )

    result = uc.execute(
        ReplayManifestRequest(manifest_id=base_manifest.manifest_id, output_dir=str(tmp_path))
    )

    assert result["status"] == "ok"
    assert generator.prompt == "prompt::with-journal"
    assert store.saved
    assert store.saved[0].parent_manifest_id == base_manifest.manifest_id
    assert Path(str(result["output_path"])).exists()


def test_retarget_journal_injects_profile_and_diff(tmp_path: Path) -> None:
    base_manifest = _base_manifest(tmp_path / "orig.png")
    store = StubManifestStore(base_manifest)
    generator = StubGenerator()
    prompt_builder = StubPromptBuilder()
    uc = RetargetJournalUseCase(
        manifest_store=store,
        generator=generator,
        prompt_builder=prompt_builder,
        default_output_dir=str(tmp_path),
        provider_name="google",
    )

    result = uc.execute(
        RetargetJournalRequest(
            manifest_id=base_manifest.manifest_id,
            target_journal="Lancet",
            output_dir=str(tmp_path),
        )
    )

    assert result["status"] == "ok"
    assert "Lancet" in generator.prompt
    assert prompt_builder.inject_target == "Lancet"
    assert store.saved
    saved = store.saved[0]
    assert saved.target_journal == "Lancet"
    assert saved.parent_manifest_id == base_manifest.manifest_id
    assert Path(saved.output_path).exists()
    profile_diff = result["journal_profile_diff"]
    assert "added" in profile_diff


def test_list_manifests_returns_public_view(tmp_path: Path) -> None:
    base_manifest = _base_manifest(tmp_path / "orig.png")
    store = StubManifestStore(base_manifest)
    uc = ListManifestsUseCase(manifest_store=store)

    result = uc.execute(ListManifestsRequest(limit=1))

    assert result["status"] == "ok"
    manifests = result["manifests"]
    assert manifests[0]["manifest_id"] == "manifest-1"
    assert "prompt_preview" in manifests[0]
