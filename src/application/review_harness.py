"""Shared review harness helpers for automated figure self-review."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.domain.interfaces import ImageVerifier


def run_quality_gate(
    verifier: ImageVerifier | None,
    image_bytes: bytes | None,
    *,
    expected_labels: list[str],
    figure_type: str,
    language: str,
    warnings: list[str],
) -> dict[str, object] | None:
    if verifier is None or image_bytes is None:
        return None

    try:
        verdict = verifier.verify(
            image_bytes,
            expected_labels=expected_labels,
            figure_type=figure_type,
            language=language,
        )
    except Exception:
        return {"passed": None, "error": "Quality gate check failed"}

    quality_gate = {
        "passed": verdict.passed,
        "total_score": verdict.total_score,
        "domain_scores": verdict.domain_scores,
        "critical_issues": list(verdict.critical_issues),
        "text_verification_passed": verdict.text_verification_passed,
        "missing_labels": list(verdict.missing_labels),
        "summary": verdict.summary,
    }
    if not verdict.passed:
        warnings.append("Quality gate FAILED — consider using edit_figure to fix issues.")
    if verdict.missing_labels:
        warnings.append(f"Missing/garbled labels: {', '.join(verdict.missing_labels)}")
    return quality_gate


def build_review_summary(
    *,
    quality_gate: dict[str, object] | None,
    provider_route_available: bool,
    host_route_available: bool = True,
    host_review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    provider_executed = quality_gate is not None
    provider_passed = _coerce_passed_flag(quality_gate)
    host_route = _normalize_host_review(host_review, available=host_route_available)
    host_passed = host_route["passed"] if isinstance(host_route["passed"], bool) else None
    provider_baseline_met = provider_passed is True
    passes_recorded = 0
    if provider_passed is True:
        passes_recorded += 1
    if host_passed is True:
        passes_recorded += 1
    requirement_met = provider_baseline_met

    if not provider_route_available:
        next_action = "configure_provider_review"
    elif not provider_executed:
        next_action = "run_provider_verify"
    elif not provider_baseline_met:
        next_action = "fix_and_rerun_provider_review"
    elif host_route_available and not host_route["executed"]:
        next_action = "optional_host_review"
    else:
        next_action = "none"

    return {
        "policy": "provider_vision_required_host_optional",
        "baseline_route": "provider_vision",
        "provider_required": True,
        "host_optional": True,
        "provider_baseline_met": provider_baseline_met,
        "passes_recorded": passes_recorded,
        "requirement_met": requirement_met,
        "accepted_review_routes": ["provider_vision", "host_vision"],
        "recommended_next_action": next_action,
        "routes": {
            "provider_vision": {
                "owner": "mcp",
                "tool": "verify_figure",
                "available": provider_route_available,
                "executed": provider_executed,
                "passed": provider_passed,
            },
            "host_vision": {
                **host_route,
            },
        },
    }


def quality_gate_snapshot(quality_gate: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(quality_gate, dict):
        return None

    return {
        "passed": quality_gate.get("passed"),
        "total_score": quality_gate.get("total_score"),
        "critical_issues": list(quality_gate.get("critical_issues") or []),
        "missing_labels": list(quality_gate.get("missing_labels") or []),
        "summary": quality_gate.get("summary"),
    }


def build_provider_review_entry(
    quality_gate: dict[str, Any] | None,
    *,
    source: str,
    reviewed_at: str | None = None,
) -> dict[str, Any] | None:
    if not isinstance(quality_gate, dict):
        return None

    return {
        "route": "provider_vision",
        "owner": "mcp",
        "tool": "verify_figure",
        "source": source,
        "passed": quality_gate.get("passed"),
        "total_score": quality_gate.get("total_score"),
        "summary": str(quality_gate.get("summary") or ""),
        "critical_issues": list(quality_gate.get("critical_issues") or []),
        "missing_labels": list(quality_gate.get("missing_labels") or []),
        "reviewed_at": reviewed_at or _utc_now_iso(),
    }


def build_host_review_entry(
    *,
    passed: bool | None,
    summary: str,
    critical_issues: list[str],
    reviewer: str,
    reviewed_at: str | None = None,
) -> dict[str, Any]:
    return {
        "route": "host_vision",
        "owner": "copilot_host",
        "tool": "record_host_review",
        "source": "host_review",
        "passed": passed,
        "summary": summary,
        "critical_issues": list(critical_issues),
        "reviewer": reviewer,
        "reviewed_at": reviewed_at or _utc_now_iso(),
    }


def append_review_history(
    history: list[dict[str, Any]],
    entry: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    normalized = [dict(item) for item in history if isinstance(item, dict)]
    if entry is not None:
        normalized.append(dict(entry))
    return normalized


def _coerce_passed_flag(quality_gate: dict[str, object] | None) -> bool | None:
    if not isinstance(quality_gate, dict):
        return None
    passed = quality_gate.get("passed")
    if isinstance(passed, bool):
        return passed
    return None


def _normalize_host_review(
    host_review: dict[str, Any] | None,
    *,
    available: bool,
) -> dict[str, Any]:
    if not isinstance(host_review, dict):
        return {
            "owner": "copilot_host",
            "tool": "record_host_review",
            "available": available,
            "executed": False,
            "passed": None,
            "status": "external",
        }

    critical_issues = host_review.get("critical_issues")
    normalized_issues = []
    if isinstance(critical_issues, list):
        normalized_issues = [str(item) for item in critical_issues]

    passed = host_review.get("passed")
    normalized_passed = passed if isinstance(passed, bool) else None
    executed = bool(host_review.get("executed", True))
    if normalized_passed is not None:
        executed = True

    return {
        "owner": str(host_review.get("owner") or "copilot_host"),
        "tool": "record_host_review",
        "available": available,
        "executed": executed,
        "passed": normalized_passed,
        "status": "recorded" if executed else "external",
        "reviewer": str(host_review.get("reviewer") or "copilot_host"),
        "summary": str(host_review.get("summary") or ""),
        "critical_issues": normalized_issues,
        "reviewed_at": str(host_review.get("reviewed_at") or ""),
    }


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()
