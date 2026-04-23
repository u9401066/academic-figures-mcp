"""Use case: load one manifest with full review history and lineage context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.application.review_harness import (
    normalize_review_history,
    normalize_review_summary,
    serialize_quality_gate_contract,
)

if TYPE_CHECKING:
    from src.domain.entities import GenerationManifest
    from src.domain.interfaces import ManifestStore


@dataclass
class GetManifestDetailRequest:
    manifest_id: str
    include_lineage: bool = True


class GetManifestDetailUseCase:
    def __init__(self, manifest_store: ManifestStore) -> None:
        self._manifest_store = manifest_store

    def execute(self, req: GetManifestDetailRequest) -> dict[str, Any]:
        manifest = self._manifest_store.load(req.manifest_id)
        lineage = self._load_lineage(manifest) if req.include_lineage else [manifest]
        review_timeline = self._build_review_timeline(lineage)

        return {
            "status": "ok",
            "manifest": self._as_manifest_entry(manifest),
            "lineage": [self._as_lineage_entry(item) for item in lineage],
            "review_timeline": review_timeline,
        }

    def _load_lineage(self, manifest: GenerationManifest) -> list[GenerationManifest]:
        lineage = [manifest]
        seen = {manifest.manifest_id}
        current = manifest
        while current.parent_manifest_id:
            parent_id = current.parent_manifest_id
            if parent_id in seen:
                break
            parent = self._manifest_store.load(parent_id)
            lineage.append(parent)
            seen.add(parent.manifest_id)
            current = parent
        lineage.reverse()
        return lineage

    def _build_review_timeline(
        self,
        lineage: list[GenerationManifest],
    ) -> list[dict[str, Any]]:
        timeline: list[dict[str, Any]] = []
        for manifest in lineage:
            for event in normalize_review_history(
                manifest.review_history,
                quality_gate=manifest.quality_gate,
                review_summary=manifest.review_summary,
                source=manifest.generation_contract,
                reviewed_at=manifest.created_at.isoformat(),
            ):
                entry = dict(event)
                entry.update(
                    {
                        "manifest_id": manifest.manifest_id,
                        "generation_contract": manifest.generation_contract,
                        "output_path": manifest.output_path,
                    }
                )
                timeline.append(entry)
        return timeline

    @staticmethod
    def _as_manifest_entry(manifest: GenerationManifest) -> dict[str, Any]:
        payload = manifest.to_dict()
        review_summary = normalize_review_summary(
            manifest.review_summary,
            quality_gate=manifest.quality_gate,
            provider_route_available=manifest.quality_gate is not None,
        )
        payload["quality_gate"] = serialize_quality_gate_contract(manifest.quality_gate)
        payload["review_summary"] = review_summary
        payload["review_history"] = normalize_review_history(
            manifest.review_history,
            quality_gate=manifest.quality_gate,
            review_summary=review_summary,
            source=manifest.generation_contract,
            reviewed_at=manifest.created_at.isoformat(),
        )
        return payload

    @staticmethod
    def _as_lineage_entry(manifest: GenerationManifest) -> dict[str, Any]:
        review_summary = normalize_review_summary(
            manifest.review_summary,
            quality_gate=manifest.quality_gate,
            provider_route_available=manifest.quality_gate is not None,
        )
        return {
            "manifest_id": manifest.manifest_id,
            "parent_manifest_id": manifest.parent_manifest_id,
            "generation_contract": manifest.generation_contract,
            "created_at": manifest.created_at.isoformat(),
            "output_path": manifest.output_path,
            "target_journal": manifest.target_journal,
            "quality_gate": serialize_quality_gate_contract(manifest.quality_gate),
            "review_summary": review_summary,
            "review_history": normalize_review_history(
                manifest.review_history,
                quality_gate=manifest.quality_gate,
                review_summary=review_summary,
                source=manifest.generation_contract,
                reviewed_at=manifest.created_at.isoformat(),
            ),
        }
