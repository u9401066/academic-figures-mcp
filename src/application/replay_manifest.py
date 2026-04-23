"""Use case: replay a generation manifest with the same prompt."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from src.application.contracts import (
    ApplicationErrorCategory,
    ApplicationStatus,
    serialize_error_contract,
    serialize_generation_result_contract,
)
from src.application.review_harness import (
    append_review_history,
    build_provider_review_entry,
    build_review_summary,
    run_quality_gate,
    serialize_public_review_payload,
)
from src.domain.entities import GenerationManifest

if TYPE_CHECKING:
    from src.domain.entities import GenerationResult
    from src.domain.interfaces import ImageGenerator, ImageVerifier, ManifestStore


@dataclass
class ReplayManifestRequest:
    manifest_id: str
    output_dir: str | None = None


class ReplayManifestUseCase:
    def __init__(
        self,
        manifest_store: ManifestStore,
        generator: ImageGenerator,
        verifier: ImageVerifier | None = None,
        default_output_dir: str = ".academic-figures/outputs",
    ) -> None:
        self._manifest_store = manifest_store
        self._generator = generator
        self._verifier = verifier
        self._output_dir = default_output_dir

    def execute(self, req: ReplayManifestRequest) -> dict[str, Any]:
        manifest = self._manifest_store.load(req.manifest_id)
        result: GenerationResult = self._generator.generate(
            prompt=manifest.prompt,
            output_size=manifest.output_size,
        )

        if not result.ok:
            error_payload: dict[str, Any] = {
                "status": ApplicationStatus.GENERATION_FAILED.value,
                "error": result.error,
                "manifest_id": req.manifest_id,
                "generation_contract": "manifest_replay",
            }
            error_payload.update(
                serialize_error_contract(
                    status=ApplicationStatus.GENERATION_FAILED,
                    category=ApplicationErrorCategory.GENERATION_RESULT,
                )
            )
            error_payload.update(serialize_generation_result_contract(result))
            return error_payload

        out_path = self._write_output(
            output_dir=req.output_dir,
            asset_kind=manifest.asset_kind,
            figure_type=manifest.figure_type,
            extension=result.file_extension,
        )
        warnings = list(manifest.warnings)
        expected_labels = _expected_labels_from_payload(manifest.planned_payload)
        quality_gate = run_quality_gate(
            self._verifier,
            result.image_bytes,
            expected_labels=expected_labels,
            figure_type=manifest.figure_type,
            language=manifest.language,
            warnings=warnings,
        )
        review_summary = build_review_summary(
            quality_gate=quality_gate,
            provider_route_available=self._verifier is not None,
        )
        review_history = append_review_history(
            [],
            build_provider_review_entry(quality_gate, source="replay_manifest"),
        )
        result.save(out_path)
        replay_manifest = self._build_manifest(
            parent=manifest,
            output_path=out_path,
            model=result.model,
            quality_gate=quality_gate,
            review_summary=review_summary,
            review_history=review_history,
            warnings=warnings,
        )
        self._manifest_store.save(replay_manifest)

        success_payload: dict[str, Any] = {
            "status": ApplicationStatus.OK.value,
            "manifest_id": replay_manifest.manifest_id,
            "parent_manifest_id": manifest.manifest_id,
            "output_path": str(out_path),
            "figure_type": manifest.figure_type,
            "render_route_used": manifest.render_route_used,
            "target_journal": manifest.target_journal,
            "journal_profile": manifest.journal_profile,
            "prompt_length": len(manifest.prompt),
            "model": result.model,
            "generation_contract": "manifest_replay",
            "warnings": warnings,
        }
        success_payload.update(
            serialize_public_review_payload(
                quality_gate=quality_gate,
                review_summary=review_summary,
                review_history=review_history,
                provider_route_available=self._verifier is not None,
                source="replay_manifest",
                reviewed_at=replay_manifest.created_at.isoformat(),
            )
        )
        success_payload.update(serialize_generation_result_contract(result))
        return success_payload

    def _write_output(
        self,
        *,
        output_dir: str | None,
        asset_kind: str,
        figure_type: str,
        extension: str,
    ) -> Path:
        base_dir = Path(output_dir or self._output_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        stem = self._slugify(f"{asset_kind}_{figure_type}_replay")
        return base_dir / f"{stem}_{ts}{extension}"

    def _build_manifest(
        self,
        *,
        parent: GenerationManifest,
        output_path: Path,
        model: str,
        quality_gate: dict[str, object] | None,
        review_summary: dict[str, object],
        review_history: list[dict[str, object]],
        warnings: list[str],
    ) -> GenerationManifest:
        return GenerationManifest(
            manifest_id=uuid4().hex,
            asset_kind=parent.asset_kind,
            figure_type=parent.figure_type,
            language=parent.language,
            output_size=parent.output_size,
            render_route_requested=parent.render_route_requested,
            render_route_used=parent.render_route_used,
            prompt=parent.prompt,
            prompt_base=parent.prompt_base or parent.prompt,
            planned_payload=dict(parent.planned_payload),
            target_journal=parent.target_journal,
            journal_profile=parent.journal_profile,
            source_context=parent.source_context,
            output_path=str(output_path),
            model=model,
            provider=parent.provider,
            generation_contract="manifest_replay",
            quality_gate=quality_gate,
            review_summary=review_summary,
            review_history=[dict(item) for item in review_history],
            parent_manifest_id=parent.manifest_id,
            warnings=warnings,
        )

    @staticmethod
    def _slugify(value: str) -> str:
        cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
        cleaned = "_".join(part for part in cleaned.split("_") if part)
        return cleaned or "asset"


def _expected_labels_from_payload(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("expected_labels")
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]
