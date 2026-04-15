from __future__ import annotations

from pathlib import Path
from typing import Any

from src.application.get_manifest_detail import GetManifestDetailRequest, GetManifestDetailUseCase
from src.application.list_manifests import ListManifestsRequest, ListManifestsUseCase
from src.application.record_host_review import RecordHostReviewRequest, RecordHostReviewUseCase
from src.application.replay_manifest import ReplayManifestRequest, ReplayManifestUseCase
from src.application.retarget_journal import RetargetJournalRequest, RetargetJournalUseCase
from src.domain.entities import GenerationManifest, GenerationResult
from src.domain.interfaces import ImageGenerator, ImageVerifier, ManifestStore, PromptBuilder
from src.domain.value_objects import QualityVerdict


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
    def __init__(
        self,
        manifest: GenerationManifest,
        extra_manifests: list[GenerationManifest] | None = None,
    ) -> None:
        self.manifest = manifest
        self.saved: list[GenerationManifest] = []
        self.records = {manifest.manifest_id: manifest}
        for item in extra_manifests or []:
            self.records[item.manifest_id] = item

    def save(self, manifest: GenerationManifest) -> GenerationManifest:
        self.saved.append(manifest)
        self.records[manifest.manifest_id] = manifest
        return manifest

    def load(self, manifest_id: str) -> GenerationManifest:
        assert manifest_id in self.records
        return self.records[manifest_id]

    def list(self, limit: int = 20) -> list[GenerationManifest]:
        manifests = [self.manifest, *self.saved]
        return manifests[:limit]


class StubVerifier(ImageVerifier):
    def __init__(self, verdict: QualityVerdict) -> None:
        self.verdict = verdict

    def verify(
        self,
        image_bytes: bytes,
        *,
        expected_labels: list[str],
        figure_type: str,
        language: str,
    ) -> QualityVerdict:
        return self.verdict


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
        quality_gate={"passed": True, "total_score": 31.0, "summary": "Base manifest passed."},
        review_summary={
            "policy": "provider_vision_required_host_optional",
            "baseline_route": "provider_vision",
            "provider_required": True,
            "host_optional": True,
            "provider_baseline_met": True,
            "passes_recorded": 1,
            "requirement_met": True,
        },
        review_history=[
            {
                "route": "provider_vision",
                "owner": "mcp",
                "tool": "verify_figure",
                "source": "generate_figure",
                "passed": True,
                "summary": "Base manifest passed.",
                "critical_issues": [],
                "missing_labels": [],
                "reviewed_at": "2026-04-15T00:00:00+00:00",
            }
        ],
        warnings=["baseline-warning"],
    )


def test_replay_manifest_reuses_prompt(tmp_path: Path) -> None:
    base_manifest = _base_manifest(tmp_path / "orig.png")
    store = StubManifestStore(base_manifest)
    generator = StubGenerator()
    verifier = StubVerifier(
        QualityVerdict(
            passed=True,
            domain_scores={"layout": 4.0},
            total_score=31.0,
            critical_issues=(),
            text_verification_passed=True,
            missing_labels=(),
            summary="Replay passed automated review.",
        )
    )
    uc = ReplayManifestUseCase(
        manifest_store=store,
        generator=generator,
        verifier=verifier,
        default_output_dir=str(tmp_path),
    )

    result = uc.execute(
        ReplayManifestRequest(manifest_id=base_manifest.manifest_id, output_dir=str(tmp_path))
    )

    assert result["status"] == "ok"
    assert generator.prompt == "prompt::with-journal"
    assert store.saved
    assert store.saved[0].parent_manifest_id == base_manifest.manifest_id
    assert store.saved[0].quality_gate == result["quality_gate"]
    assert store.saved[0].review_summary == result["review_summary"]
    assert store.saved[0].review_history == result["review_history"]
    assert result["review_summary"]["provider_baseline_met"] is True
    assert result["review_summary"]["requirement_met"] is True
    assert Path(str(result["output_path"])).exists()


def test_retarget_journal_injects_profile_and_diff(tmp_path: Path) -> None:
    base_manifest = _base_manifest(tmp_path / "orig.png")
    store = StubManifestStore(base_manifest)
    generator = StubGenerator()
    prompt_builder = StubPromptBuilder()
    verifier = StubVerifier(
        QualityVerdict(
            passed=True,
            domain_scores={"layout": 4.0},
            total_score=32.0,
            critical_issues=(),
            text_verification_passed=True,
            missing_labels=(),
            summary="Retarget passed automated review.",
        )
    )
    uc = RetargetJournalUseCase(
        manifest_store=store,
        generator=generator,
        prompt_builder=prompt_builder,
        verifier=verifier,
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
    assert saved.review_summary["provider_baseline_met"] is True
    assert saved.review_summary["requirement_met"] is True
    assert saved.review_history[0]["route"] == "provider_vision"
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
    assert manifests[0]["quality_gate"]["passed"] is True
    assert manifests[0]["review_summary"]["provider_baseline_met"] is True
    assert manifests[0]["review_summary"]["requirement_met"] is True
    assert manifests[0]["review_history_count"] == 1


def test_record_host_review_updates_manifest_review_summary(tmp_path: Path) -> None:
    base_manifest = _base_manifest(tmp_path / "orig.png")
    store = StubManifestStore(base_manifest)
    uc = RecordHostReviewUseCase(manifest_store=store)

    result = uc.execute(
        RecordHostReviewRequest(
            manifest_id=base_manifest.manifest_id,
            passed=True,
            summary="Copilot visual review confirms labels and composition.",
            critical_issues=[],
        )
    )

    assert result["status"] == "ok"
    assert store.saved
    saved = store.saved[0]
    assert saved.manifest_id == base_manifest.manifest_id
    assert saved.review_summary["passes_recorded"] == 2
    assert saved.review_summary["provider_baseline_met"] is True
    assert saved.review_summary["routes"]["host_vision"]["executed"] is True
    assert saved.review_summary["routes"]["host_vision"]["passed"] is True
    assert len(saved.review_history) == 2
    assert saved.review_history[-1]["route"] == "host_vision"


def test_record_host_review_cannot_replace_failed_provider_baseline(tmp_path: Path) -> None:
    base_manifest = _base_manifest(tmp_path / "orig.png")
    base_manifest.quality_gate = {"passed": False, "summary": "Provider gate failed."}
    base_manifest.review_summary = {
        "policy": "provider_vision_required_host_optional",
        "baseline_route": "provider_vision",
        "provider_required": True,
        "host_optional": True,
        "provider_baseline_met": False,
        "passes_recorded": 0,
        "requirement_met": False,
    }
    store = StubManifestStore(base_manifest)
    uc = RecordHostReviewUseCase(manifest_store=store)

    result = uc.execute(
        RecordHostReviewRequest(
            manifest_id=base_manifest.manifest_id,
            passed=True,
            summary="Host review looks acceptable.",
            critical_issues=[],
        )
    )

    assert result["status"] == "ok"
    assert result["review_summary"]["passes_recorded"] == 1
    assert result["review_summary"]["provider_baseline_met"] is False
    assert result["review_summary"]["requirement_met"] is False


def test_get_manifest_detail_returns_lineage_and_review_timeline(tmp_path: Path) -> None:
    base_manifest = _base_manifest(tmp_path / "orig.png")
    child_manifest = GenerationManifest(
        manifest_id="manifest-2",
        asset_kind=base_manifest.asset_kind,
        figure_type=base_manifest.figure_type,
        language=base_manifest.language,
        output_size=base_manifest.output_size,
        render_route_requested=base_manifest.render_route_requested,
        render_route_used=base_manifest.render_route_used,
        prompt="prompt::with-journal::replay",
        prompt_base=base_manifest.prompt_base,
        planned_payload=dict(base_manifest.planned_payload),
        target_journal=base_manifest.target_journal,
        journal_profile=base_manifest.journal_profile,
        source_context=dict(base_manifest.source_context),
        output_path=str(tmp_path / "child.png"),
        model="stub-model-v2",
        provider="google",
        generation_contract="manifest_replay",
        quality_gate={"passed": False, "summary": "Replay needs edits."},
        review_summary={
            "policy": "provider_vision_required_host_optional",
            "baseline_route": "provider_vision",
            "provider_required": True,
            "host_optional": True,
            "provider_baseline_met": False,
            "passes_recorded": 0,
            "requirement_met": False,
        },
        review_history=[
            {
                "route": "provider_vision",
                "owner": "mcp",
                "tool": "verify_figure",
                "source": "replay_manifest",
                "passed": False,
                "summary": "Replay needs edits.",
                "critical_issues": [],
                "missing_labels": [],
                "reviewed_at": "2026-04-15T01:00:00+00:00",
            }
        ],
        parent_manifest_id=base_manifest.manifest_id,
        warnings=[],
    )
    store = StubManifestStore(base_manifest, extra_manifests=[child_manifest])
    uc = GetManifestDetailUseCase(manifest_store=store)

    result = uc.execute(
        GetManifestDetailRequest(
            manifest_id=child_manifest.manifest_id,
            include_lineage=True,
        )
    )

    assert result["status"] == "ok"
    assert result["manifest"]["manifest_id"] == "manifest-2"
    assert len(result["lineage"]) == 2
    assert result["lineage"][0]["manifest_id"] == "manifest-1"
    assert result["lineage"][1]["manifest_id"] == "manifest-2"
    assert len(result["review_timeline"]) == 2
    assert result["review_timeline"][0]["manifest_id"] == "manifest-1"
    assert result["review_timeline"][1]["manifest_id"] == "manifest-2"
