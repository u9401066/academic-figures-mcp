"""Use case: list persisted manifests for discovery and replay."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.domain.entities import GenerationManifest
    from src.domain.interfaces import ManifestStore


@dataclass
class ListManifestsRequest:
    limit: int = 20


class ListManifestsUseCase:
    def __init__(self, manifest_store: ManifestStore) -> None:
        self._manifest_store = manifest_store

    def execute(self, req: ListManifestsRequest) -> dict[str, Any]:
        manifests = self._manifest_store.list(limit=req.limit)
        return {
            "status": "ok",
            "manifests": [self._as_public_manifest(m) for m in manifests],
        }

    @staticmethod
    def _as_public_manifest(manifest: GenerationManifest) -> dict[str, Any]:
        prompt_preview = manifest.prompt.strip().splitlines()[0:2]
        return {
            "manifest_id": manifest.manifest_id,
            "parent_manifest_id": manifest.parent_manifest_id,
            "asset_kind": manifest.asset_kind,
            "figure_type": manifest.figure_type,
            "target_journal": manifest.target_journal,
            "render_route_used": manifest.render_route_used,
            "output_path": manifest.output_path,
            "provider": manifest.provider,
            "model": manifest.model,
            "created_at": manifest.created_at.isoformat(),
            "source_context": manifest.source_context,
            "prompt_preview": "\n".join(prompt_preview),
        }
