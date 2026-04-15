"""Use case: record a host-side visual review result against a manifest."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from src.application.review_harness import (
    append_review_history,
    build_host_review_entry,
    build_review_summary,
)
from src.domain.exceptions import ValidationError

if TYPE_CHECKING:
    from src.domain.interfaces import ManifestStore


@dataclass
class RecordHostReviewRequest:
    manifest_id: str
    passed: bool
    summary: str
    critical_issues: list[str] | None = None
    reviewer: str = "copilot_host"

    def __post_init__(self) -> None:
        self.manifest_id = self.manifest_id.strip()
        self.summary = self.summary.strip()
        self.reviewer = self.reviewer.strip() or "copilot_host"
        self.critical_issues = [
            item.strip() for item in (self.critical_issues or []) if item.strip()
        ]
        if not self.manifest_id:
            raise ValidationError("manifest_id is required")
        if not self.summary:
            raise ValidationError("summary cannot be blank")


class RecordHostReviewUseCase:
    def __init__(self, manifest_store: ManifestStore) -> None:
        self._manifest_store = manifest_store

    def execute(self, req: RecordHostReviewRequest) -> dict[str, Any]:
        manifest = self._manifest_store.load(req.manifest_id)
        existing_routes = _extract_routes(manifest.review_summary)
        provider_route = existing_routes.get("provider_vision")
        provider_available = bool(
            provider_route.get("available", manifest.quality_gate is not None)
            if isinstance(provider_route, dict)
            else manifest.quality_gate is not None
        )
        reviewed_at = datetime.now(tz=timezone.utc).isoformat()
        host_route = {
            "owner": "copilot_host",
            "reviewer": req.reviewer,
            "executed": True,
            "passed": req.passed,
            "summary": req.summary,
            "critical_issues": list(req.critical_issues or []),
            "reviewed_at": reviewed_at,
        }
        host_entry = build_host_review_entry(
            passed=req.passed,
            summary=req.summary,
            critical_issues=list(req.critical_issues or []),
            reviewer=req.reviewer,
            reviewed_at=reviewed_at,
        )
        review_summary = build_review_summary(
            quality_gate=manifest.quality_gate,
            provider_route_available=provider_available,
            host_review=host_route,
        )
        manifest.review_history = append_review_history(manifest.review_history, host_entry)
        manifest.review_summary = review_summary
        self._manifest_store.save(manifest)

        return {
            "status": "ok",
            "manifest_id": manifest.manifest_id,
            "quality_gate": manifest.quality_gate,
            "review_summary": review_summary,
        }


def _extract_routes(review_summary: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(review_summary, dict):
        return {}
    routes = review_summary.get("routes")
    return routes if isinstance(routes, dict) else {}
