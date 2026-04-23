"""Typed public status contracts for application-layer responses."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from src.domain.exceptions import ConfigurationError, DomainError, ValidationError

if TYPE_CHECKING:
    from src.domain.entities import GenerationResult


class ApplicationStatus(Enum):
    OK = "ok"
    ERROR = "error"
    GENERATION_FAILED = "generation_failed"
    EDIT_FAILED = "edit_failed"
    UNSUPPORTED_RENDER_ROUTE = "unsupported_render_route"


class ReviewRoute(Enum):
    PROVIDER_VISION = "provider_vision"
    HOST_VISION = "host_vision"


class ReviewStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class ReviewRouteStatus(Enum):
    NOT_AVAILABLE = "not_available"
    NOT_RUN = "not_run"
    EXECUTED = "executed"
    RECORDED = "recorded"
    EXTERNAL = "external"


class ApplicationErrorCategory(Enum):
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    DOMAIN = "domain"
    UNSUPPORTED = "unsupported"
    CONTRACT = "contract"
    EXECUTION = "execution"
    GENERATION_RESULT = "generation_result"
    UNKNOWN = "unknown"


class AggregateKind(Enum):
    BATCH_GENERATE = "batch_generate"
    LIST_MANIFESTS = "list_manifests"


class AggregateStatus(Enum):
    COMPLETE_SUCCESS = "complete_success"
    COMPLETE_PARTIAL_FAILURE = "complete_partial_failure"
    COMPLETE_FAILURE = "complete_failure"
    LIST_READY = "list_ready"


def serialize_generation_result_contract(result: GenerationResult) -> dict[str, object]:
    """Expose a stable status/error contract for result-bearing responses."""

    assert result.status is not None
    return {
        "result_status": result.status.value,
        "error_kind": result.error_kind.value if result.error_kind is not None else None,
    }


def serialize_review_contract(
    *,
    route: ReviewRoute,
    passed: bool | None,
    error: str | None = None,
) -> dict[str, object]:
    """Expose a stable review outcome contract."""

    return {
        "review_route": route.value,
        "review_status": _review_status(passed=passed, error=error).value,
    }


def serialize_review_route_contract(
    *,
    route: ReviewRoute,
    route_status: ReviewRouteStatus,
    passed: bool | None,
    error: str | None = None,
) -> dict[str, object]:
    """Expose a stable route-level review contract."""

    payload = serialize_review_contract(route=route, passed=passed, error=error)
    payload["route"] = route.value
    payload["route_status"] = route_status.value
    return payload


def prefix_contract(prefix: str, values: dict[str, object]) -> dict[str, object]:
    """Prefix serialized contract fields for nested payloads."""

    return {f"{prefix}_{key}": value for key, value in values.items()}


def serialize_error_contract(
    *,
    status: ApplicationStatus,
    category: ApplicationErrorCategory,
) -> dict[str, object]:
    """Expose a stable error contract for host-facing failures."""

    return {
        "error_status": status.value,
        "error_category": category.value,
    }


def serialize_aggregate_contract(
    *,
    kind: AggregateKind,
    item_count: int,
    total_count: int | None = None,
    success_count: int | None = None,
    failed_count: int | None = None,
) -> dict[str, object]:
    """Expose a stable aggregate summary contract for batch/list-style responses."""

    payload: dict[str, object] = {
        "aggregate_kind": kind.value,
        "aggregate_status": _aggregate_status(
            kind=kind,
            item_count=item_count,
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count,
        ).value,
        "item_count": item_count,
    }
    if total_count is not None:
        payload["total_count"] = total_count
    if success_count is not None:
        payload["success_count"] = success_count
    if failed_count is not None:
        payload["failed_count"] = failed_count
    return payload


def serialize_exception_contract(error: Exception) -> dict[str, object]:
    """Map exceptions to the shared host-facing error contract."""

    return serialize_error_contract(
        status=ApplicationStatus.ERROR,
        category=_exception_category(error),
    )


def _exception_category(error: Exception) -> ApplicationErrorCategory:
    if isinstance(error, ValidationError):
        return ApplicationErrorCategory.VALIDATION
    if isinstance(error, ConfigurationError):
        return ApplicationErrorCategory.CONFIGURATION
    if isinstance(error, DomainError):
        return ApplicationErrorCategory.DOMAIN
    return ApplicationErrorCategory.UNKNOWN


def _aggregate_status(
    *,
    kind: AggregateKind,
    item_count: int,
    total_count: int | None,
    success_count: int | None,
    failed_count: int | None,
) -> AggregateStatus:
    if kind is AggregateKind.LIST_MANIFESTS:
        return AggregateStatus.LIST_READY
    if total_count is None or success_count is None or failed_count is None:
        raise ValueError("batch aggregate contract requires total/success/failed counts")
    if item_count > 0 and failed_count == 0:
        return AggregateStatus.COMPLETE_SUCCESS
    if success_count == 0:
        return AggregateStatus.COMPLETE_FAILURE
    return AggregateStatus.COMPLETE_PARTIAL_FAILURE


def _review_status(*, passed: bool | None, error: str | None) -> ReviewStatus:
    if error:
        return ReviewStatus.ERROR
    if passed is True:
        return ReviewStatus.PASSED
    if passed is False:
        return ReviewStatus.FAILED
    return ReviewStatus.SKIPPED
