"""Shared review harness helpers for automated figure self-review."""

from __future__ import annotations

import contextlib
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from src.application.contracts import (
    ReviewRoute,
    ReviewRouteStatus,
    serialize_review_contract,
    serialize_review_route_contract,
)

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
        error = "Quality gate check failed"
        return {
            "passed": None,
            "error": error,
            **serialize_review_contract(
                route=ReviewRoute.PROVIDER_VISION,
                passed=None,
                error=error,
            ),
        }

    quality_gate = {
        "passed": verdict.passed,
        "total_score": verdict.total_score,
        "domain_scores": verdict.domain_scores,
        "critical_issues": list(verdict.critical_issues),
        "text_verification_passed": verdict.text_verification_passed,
        "missing_labels": list(verdict.missing_labels),
        "summary": verdict.summary,
        **serialize_review_contract(
            route=ReviewRoute.PROVIDER_VISION,
            passed=verdict.passed,
        ),
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
    provider_error = _coerce_error_text(quality_gate)
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

    provider_route_status = _provider_route_status(
        available=provider_route_available,
        executed=provider_executed,
    )

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
                **serialize_review_route_contract(
                    route=ReviewRoute.PROVIDER_VISION,
                    route_status=provider_route_status,
                    passed=provider_passed,
                    error=provider_error,
                ),
                "owner": "mcp",
                "tool": "verify_figure",
                "available": provider_route_available,
                "executed": provider_executed,
                "passed": provider_passed,
                "status": provider_route_status.value,
            },
            "host_vision": {
                **host_route,
            },
        },
    }


def quality_gate_snapshot(quality_gate: dict[str, Any] | None) -> dict[str, Any] | None:
    serialized = serialize_quality_gate_contract(quality_gate)
    if serialized is None:
        return None

    return {
        "route": serialized.get("route"),
        "route_status": serialized.get("route_status"),
        "review_route": serialized.get("review_route"),
        "review_status": serialized.get("review_status"),
        "passed": serialized.get("passed"),
        "total_score": serialized.get("total_score"),
        "critical_issues": list(serialized.get("critical_issues") or []),
        "missing_labels": list(serialized.get("missing_labels") or []),
        "summary": serialized.get("summary"),
    }


def serialize_quality_gate_contract(
    quality_gate: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(quality_gate, dict):
        return None

    serialized = dict(quality_gate)
    serialized.update(
        serialize_review_route_contract(
            route=ReviewRoute.PROVIDER_VISION,
            route_status=ReviewRouteStatus.EXECUTED,
            passed=_coerce_passed_flag(quality_gate),
            error=_coerce_error_text(quality_gate),
        )
    )
    serialized["status"] = str(
        serialized.get("status") or ReviewRouteStatus.EXECUTED.value
    )
    return serialized


def normalize_review_summary(
    review_summary: dict[str, Any] | None,
    *,
    quality_gate: dict[str, Any] | None,
    provider_route_available: bool,
) -> dict[str, Any]:
    routes = _extract_routes(review_summary)
    provider_route = routes.get(ReviewRoute.PROVIDER_VISION.value)
    host_route = routes.get(ReviewRoute.HOST_VISION.value)

    provider_available = _route_available(provider_route, default=provider_route_available)
    host_available = _route_available(host_route, default=True)

    return build_review_summary(
        quality_gate=quality_gate,
        provider_route_available=provider_available,
        host_route_available=host_available,
        host_review=host_route if isinstance(host_route, dict) else None,
    )


def normalize_review_history(
    review_history: list[dict[str, Any]],
    *,
    quality_gate: dict[str, Any] | None,
    review_summary: dict[str, Any] | None,
    source: str,
    reviewed_at: str,
) -> list[dict[str, Any]]:
    normalized = [
        _normalize_review_entry(item)
        for item in review_history
        if isinstance(item, dict)
    ]
    if normalized:
        return normalized

    provider_entry = build_provider_review_entry(
        quality_gate,
        source=source,
        reviewed_at=reviewed_at,
    )
    history = append_review_history([], provider_entry)

    host_route = _host_route_from_summary(review_summary)
    if host_route is not None:
        history = append_review_history(
            history,
            build_host_review_entry(
                passed=(
                    host_route.get("passed")
                    if isinstance(host_route.get("passed"), bool)
                    else None
                ),
                summary=str(host_route.get("summary") or ""),
                critical_issues=[
                    str(item) for item in (host_route.get("critical_issues") or [])
                ],
                reviewer=str(host_route.get("reviewer") or "copilot_host"),
                reviewed_at=str(host_route.get("reviewed_at") or reviewed_at),
            ),
        )
    return history


def serialize_public_review_payload(
    *,
    quality_gate: dict[str, Any] | None,
    review_summary: dict[str, Any] | None,
    review_history: list[dict[str, Any]],
    provider_route_available: bool,
    source: str,
    reviewed_at: str,
) -> dict[str, Any]:
    normalized_summary = normalize_review_summary(
        review_summary,
        quality_gate=quality_gate,
        provider_route_available=provider_route_available,
    )
    normalized_history = normalize_review_history(
        review_history,
        quality_gate=quality_gate,
        review_summary=normalized_summary,
        source=source,
        reviewed_at=reviewed_at,
    )
    return {
        "quality_gate": serialize_quality_gate_contract(quality_gate),
        "review_summary": normalized_summary,
        "review_history": normalized_history,
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
        **serialize_review_route_contract(
            route=ReviewRoute.PROVIDER_VISION,
            route_status=ReviewRouteStatus.RECORDED,
            passed=_coerce_passed_flag(quality_gate),
            error=_coerce_error_text(quality_gate),
        ),
        "route": "provider_vision",
        "status": ReviewRouteStatus.RECORDED.value,
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
        **serialize_review_route_contract(
            route=ReviewRoute.HOST_VISION,
            route_status=ReviewRouteStatus.RECORDED,
            passed=passed,
        ),
        "route": "host_vision",
        "status": ReviewRouteStatus.RECORDED.value,
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


def _extract_routes(review_summary: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(review_summary, dict):
        return {}
    routes = review_summary.get("routes")
    return routes if isinstance(routes, dict) else {}


def _host_route_from_summary(review_summary: dict[str, Any] | None) -> dict[str, Any] | None:
    host_route = _extract_routes(review_summary).get(ReviewRoute.HOST_VISION.value)
    if not isinstance(host_route, dict):
        return None
    if not host_route.get("executed"):
        return None
    return host_route


def _route_available(route: Any, *, default: bool) -> bool:
    if isinstance(route, dict) and isinstance(route.get("available"), bool):
        return bool(route["available"])
    return default


def _normalize_review_entry(entry: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(entry)
    route = _review_route_from_value(normalized.get("route"))
    if route is None:
        return normalized

    route_status = _entry_route_status(normalized)
    passed = (
        normalized.get("passed") if isinstance(normalized.get("passed"), bool) else None
    )
    error = str(normalized.get("error") or "") or None
    normalized.update(
        serialize_review_route_contract(
            route=route,
            route_status=route_status,
            passed=passed,
            error=error,
        )
    )
    normalized["status"] = route_status.value
    return normalized


def _review_route_from_value(value: object) -> ReviewRoute | None:
    if not isinstance(value, str):
        return None
    with contextlib.suppress(ValueError):
        return ReviewRoute(value)
    return None


def _entry_route_status(entry: dict[str, Any]) -> ReviewRouteStatus:
    route_status = entry.get("route_status") or entry.get("status")
    if isinstance(route_status, str):
        with contextlib.suppress(ValueError):
            return ReviewRouteStatus(route_status)
    return ReviewRouteStatus.RECORDED


def _normalize_host_review(
    host_review: dict[str, Any] | None,
    *,
    available: bool,
) -> dict[str, Any]:
    if not isinstance(host_review, dict):
        route_status = (
            ReviewRouteStatus.EXTERNAL if available else ReviewRouteStatus.NOT_AVAILABLE
        )
        return {
            **serialize_review_route_contract(
                route=ReviewRoute.HOST_VISION,
                route_status=route_status,
                passed=None,
            ),
            "owner": "copilot_host",
            "tool": "record_host_review",
            "available": available,
            "executed": False,
            "passed": None,
            "status": route_status.value,
            "reviewer": "copilot_host",
            "summary": "",
            "critical_issues": [],
            "reviewed_at": "",
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
    route_status = _host_route_status(available=available, executed=executed)
    error_text = str(host_review.get("error") or "") or None

    return {
        **serialize_review_route_contract(
            route=ReviewRoute.HOST_VISION,
            route_status=route_status,
            passed=normalized_passed,
            error=error_text,
        ),
        "owner": str(host_review.get("owner") or "copilot_host"),
        "tool": "record_host_review",
        "available": available,
        "executed": executed,
        "passed": normalized_passed,
        "status": route_status.value,
        "reviewer": str(host_review.get("reviewer") or "copilot_host"),
        "summary": str(host_review.get("summary") or ""),
        "critical_issues": normalized_issues,
        "reviewed_at": str(host_review.get("reviewed_at") or ""),
    }


def _coerce_error_text(quality_gate: dict[str, object] | None) -> str | None:
    if not isinstance(quality_gate, dict):
        return None
    error = quality_gate.get("error")
    if isinstance(error, str) and error:
        return error
    return None


def _provider_route_status(*, available: bool, executed: bool) -> ReviewRouteStatus:
    if not available:
        return ReviewRouteStatus.NOT_AVAILABLE
    if executed:
        return ReviewRouteStatus.EXECUTED
    return ReviewRouteStatus.NOT_RUN


def _host_route_status(*, available: bool, executed: bool) -> ReviewRouteStatus:
    if not available:
        return ReviewRouteStatus.NOT_AVAILABLE
    if executed:
        return ReviewRouteStatus.RECORDED
    return ReviewRouteStatus.EXTERNAL


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()
