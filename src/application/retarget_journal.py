"""Use case: retarget a saved manifest to a new journal profile."""

from __future__ import annotations

import json
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
    from src.domain.interfaces import ImageGenerator, ImageVerifier, ManifestStore, PromptBuilder


@dataclass
class RetargetJournalRequest:
    manifest_id: str
    target_journal: str
    output_dir: str | None = None


class RetargetJournalUseCase:
    def __init__(
        self,
        manifest_store: ManifestStore,
        generator: ImageGenerator,
        prompt_builder: PromptBuilder,
        verifier: ImageVerifier | None = None,
        default_output_dir: str = ".academic-figures/outputs",
        provider_name: str = "google",
    ) -> None:
        self._manifest_store = manifest_store
        self._generator = generator
        self._prompt_builder = prompt_builder
        self._verifier = verifier
        self._output_dir = default_output_dir
        self._provider_name = provider_name

    def execute(self, req: RetargetJournalRequest) -> dict[str, Any]:
        manifest = self._manifest_store.load(req.manifest_id)
        base_prompt = manifest.prompt_base or manifest.prompt
        source_journal = ""
        if isinstance(manifest.source_context, dict):
            source_journal = str(manifest.source_context.get("journal") or "")

        retargeted_prompt, profile = self._prompt_builder.inject_journal_requirements(
            base_prompt,
            target_journal=req.target_journal,
            source_journal=source_journal,
        )
        profile_diff = self._profile_diff(manifest.journal_profile, profile)

        result: GenerationResult = self._generator.generate(
            prompt=retargeted_prompt,
            output_size=manifest.output_size,
        )
        if not result.ok:
            error_payload: dict[str, Any] = {
                "status": ApplicationStatus.GENERATION_FAILED.value,
                "generation_contract": "journal_retarget",
                "error": result.error,
                "manifest_id": req.manifest_id,
                "target_journal": req.target_journal,
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
            target_journal=req.target_journal,
            extension=result.file_extension,
        )
        warnings = list(manifest.warnings)
        if req.target_journal and profile is None:
            warnings.append(
                f"No journal profile matched target_journal '{req.target_journal}'; "
                "using generic academic defaults."
            )
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
            build_provider_review_entry(quality_gate, source="retarget_journal"),
        )
        result.save(out_path)
        retargeted_manifest = self._build_manifest(
            parent=manifest,
            target_journal=req.target_journal,
            journal_profile=profile,
            output_path=out_path,
            prompt=retargeted_prompt,
            model=result.model,
            quality_gate=quality_gate,
            review_summary=review_summary,
            review_history=review_history,
            warnings=warnings,
        )
        self._manifest_store.save(retargeted_manifest)

        success_payload: dict[str, Any] = {
            "status": ApplicationStatus.OK.value,
            "manifest_id": retargeted_manifest.manifest_id,
            "parent_manifest_id": manifest.manifest_id,
            "output_path": str(out_path),
            "target_journal": req.target_journal,
            "journal_profile": profile,
            "journal_profile_diff": profile_diff,
            "render_route_used": manifest.render_route_used,
            "model": result.model,
            "generation_contract": "journal_retarget",
            "warnings": warnings,
        }
        success_payload.update(
            serialize_public_review_payload(
                quality_gate=quality_gate,
                review_summary=review_summary,
                review_history=review_history,
                provider_route_available=self._verifier is not None,
                source="retarget_journal",
                reviewed_at=retargeted_manifest.created_at.isoformat(),
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
        target_journal: str,
        extension: str,
    ) -> Path:
        base_dir = Path(output_dir or self._output_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        journal_slug = self._slugify(target_journal or "journal")
        stem = self._slugify(f"{asset_kind}_{figure_type}_{journal_slug}")
        return base_dir / f"{stem}_{ts}{extension}"

    def _build_manifest(
        self,
        *,
        parent: GenerationManifest,
        target_journal: str,
        journal_profile: dict[str, object] | None,
        output_path: Path,
        prompt: str,
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
            prompt=prompt,
            prompt_base=parent.prompt_base or parent.prompt,
            planned_payload=dict(parent.planned_payload),
            target_journal=target_journal,
            journal_profile=journal_profile,
            source_context=parent.source_context,
            output_path=str(output_path),
            model=model,
            provider=self._provider_name,
            generation_contract="journal_retarget",
            quality_gate=quality_gate,
            review_summary=review_summary,
            review_history=[dict(item) for item in review_history],
            parent_manifest_id=parent.manifest_id,
            warnings=warnings,
        )

    @staticmethod
    def _profile_diff(
        before: dict[str, object] | None,
        after: dict[str, object] | None,
    ) -> dict[str, list[str]]:
        before_set = RetargetJournalUseCase._profile_lines(before)
        after_set = RetargetJournalUseCase._profile_lines(after)
        return {
            "added": sorted(after_set - before_set),
            "removed": sorted(before_set - after_set),
            "unchanged": sorted(before_set & after_set),
        }

    @staticmethod
    def _profile_lines(profile: dict[str, object] | None) -> set[str]:
        if not isinstance(profile, dict):
            return set()
        lines: set[str] = set()
        for key, value in sorted(profile.items()):
            if isinstance(value, (dict, list)):
                value_text = json.dumps(value, sort_keys=True)
            else:
                value_text = str(value)
            lines.add(f"{key}={value_text}")
        return lines

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
