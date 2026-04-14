from __future__ import annotations

from datetime import datetime, timezone

from src.domain.entities import GenerationManifest


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
        created_at=datetime(2026, 4, 14, 8, 30, tzinfo=timezone.utc),
        parent_manifest_id="manifest-122",
        warnings=["journal profile applied"],
    )

    restored = GenerationManifest.from_dict(manifest.to_dict())

    assert restored == manifest
