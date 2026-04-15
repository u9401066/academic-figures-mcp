"""Use case: load one manifest with full review history and lineage context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.application.review_harness import (
    append_review_history,
    build_host_review_entry,
    build_provider_review_entry,
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
            "manifest": manifest.to_dict(),
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
            for event in self._effective_review_history(manifest):
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
    def _as_lineage_entry(manifest: GenerationManifest) -> dict[str, Any]:
        return {
            "manifest_id": manifest.manifest_id,
            "parent_manifest_id": manifest.parent_manifest_id,
            "generation_contract": manifest.generation_contract,
            "created_at": manifest.created_at.isoformat(),
            "output_path": manifest.output_path,
            "target_journal": manifest.target_journal,
            "quality_gate": manifest.quality_gate,
            "review_summary": manifest.review_summary,
            "review_history": [dict(item) for item in manifest.review_history],
        }

    @staticmethod
    def _effective_review_history(manifest: GenerationManifest) -> list[dict[str, Any]]:
        history = append_review_history([], None)
        for item in manifest.review_history:
            if isinstance(item, dict):
                history.append(dict(item))
        if history:
            return history

        provider_entry = build_provider_review_entry(
            manifest.quality_gate,
            source=manifest.generation_contract,
            reviewed_at=manifest.created_at.isoformat(),
        )
        history = append_review_history(history, provider_entry)

        host_route = _host_route_from_summary(manifest.review_summary)
        if host_route is not None:
            history = append_review_history(
                history,
                build_host_review_entry(
                    passed=host_route.get("passed")
                    if isinstance(host_route.get("passed"), bool)
                    else None,
                    summary=str(host_route.get("summary") or ""),
                    critical_issues=[
                        str(item) for item in (host_route.get("critical_issues") or [])
                    ],
                    reviewer=str(host_route.get("reviewer") or "copilot_host"),
                    reviewed_at=str(
                        host_route.get("reviewed_at") or manifest.created_at.isoformat()
                    ),
                ),
            )
        return history


def _host_route_from_summary(review_summary: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(review_summary, dict):
        return None
    routes = review_summary.get("routes")
    if not isinstance(routes, dict):
        return None
    host_route = routes.get("host_vision")
    if not isinstance(host_route, dict):
        return None
    if not host_route.get("executed"):
        return None
    return host_route
