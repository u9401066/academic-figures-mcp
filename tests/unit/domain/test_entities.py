from __future__ import annotations

from datetime import datetime, timezone

from src.domain.entities import (
    GenerationErrorKind,
    GenerationManifest,
    GenerationResult,
    GenerationResultStatus,
)


def test_generation_result_infers_image_ready_status() -> None:
    result = GenerationResult(image_bytes=b"png")

    assert result.status is GenerationResultStatus.IMAGE_READY
    assert result.ok is True
    assert result.succeeded is True
    assert result.error_kind is None


def test_generation_result_infers_text_ready_status_even_with_warning_text() -> None:
    result = GenerationResult(text="partial evaluation", error="provider warning")

    assert result.status is GenerationResultStatus.TEXT_READY
    assert result.ok is False
    assert result.succeeded is True
    assert result.error_kind is None


def test_generation_result_infers_failed_status_and_unknown_error_kind() -> None:
    result = GenerationResult(error="provider failed")

    assert result.status is GenerationResultStatus.FAILED
    assert result.ok is False
    assert result.succeeded is False
    assert result.error_kind is GenerationErrorKind.UNKNOWN


def test_generation_manifest_round_trip_from_dict() -> None:
    manifest = GenerationManifest(
        manifest_id="manifest-123",
        asset_kind="academic_figure",
        figure_type="infographic",
        language="zh-TW",
        output_size="1024x1536",
        render_route_requested="image_generation",
        render_route_used="image_generation",
        prompt="full prompt",
        prompt_base="base prompt",
        planned_payload={"asset_kind": "academic_figure", "selected_figure_type": "infographic"},
        target_journal="Nature",
        journal_profile={"id": "nature_portfolio", "display_name": "Nature Portfolio"},
        source_context={"pmid": "12345678", "journal": "Nature"},
        output_path="outputs/figure.png",
        model="gemini-2.5-flash-image-preview",
        provider="google",
        generation_contract="planned_payload",
        quality_gate={
            "passed": True,
            "total_score": 33.0,
            "missing_labels": [],
            "summary": "Passed automated review.",
        },
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
                "summary": "Passed automated review.",
                "critical_issues": [],
                "missing_labels": [],
                "reviewed_at": "2026-04-14T08:31:00+00:00",
            }
        ],
        created_at=datetime(2026, 4, 14, 8, 30, tzinfo=timezone.utc),
        parent_manifest_id="manifest-122",
        warnings=["journal profile applied"],
    )

    restored = GenerationManifest.from_dict(manifest.to_dict())

    assert restored == manifest


def test_generation_manifest_round_trip_preserves_absent_target_journal() -> None:
    manifest = GenerationManifest(
        manifest_id="manifest-no-journal",
        asset_kind="academic_figure",
        figure_type="infographic",
        language="en",
        output_size="1024x1024",
        render_route_requested="image_generation",
        render_route_used="image_generation",
        prompt="prompt",
        prompt_base="prompt",
        planned_payload={},
        target_journal=None,
        journal_profile=None,
        source_context={},
        output_path="outputs/figure.png",
        model="stub-model",
        provider="google",
        generation_contract="planned_payload",
    )

    restored = GenerationManifest.from_dict(manifest.to_dict())

    assert restored.target_journal is None
    assert restored.to_dict()["target_journal"] is None
