"""Use case: post-generation quality gate via vision self-check."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from src.application.contracts import (
    ApplicationStatus,
    ReviewRoute,
    ReviewRouteStatus,
    serialize_review_route_contract,
)
from src.domain.exceptions import ImageNotFoundError

if TYPE_CHECKING:
    from src.domain.interfaces import ImageVerifier


@dataclass
class VerifyFigureRequest:
    image_path: str
    expected_labels: list[str]
    figure_type: str = "infographic"
    language: str = "zh-TW"


class VerifyFigureUseCase:
    """Run the automated quality gate on a generated figure.

    Returns a structured verdict including domain scores, label verification,
    and a pass/fail decision.
    """

    def __init__(self, verifier: ImageVerifier) -> None:
        self._verifier = verifier

    def execute(self, req: VerifyFigureRequest) -> dict[str, object]:
        img = Path(req.image_path)
        if not img.exists():
            raise ImageNotFoundError(f"Image not found: {req.image_path}")

        image_bytes = img.read_bytes()

        verdict = self._verifier.verify(
            image_bytes,
            expected_labels=req.expected_labels,
            figure_type=req.figure_type,
            language=req.language,
        )

        payload = {
            "status": ApplicationStatus.OK.value,
            "passed": verdict.passed,
            "total_score": verdict.total_score,
            "domain_scores": verdict.domain_scores,
            "critical_issues": list(verdict.critical_issues),
            "text_verification_passed": verdict.text_verification_passed,
            "missing_labels": list(verdict.missing_labels),
            "summary": verdict.summary,
            "image_path": str(img),
            "figure_type": req.figure_type,
            "language": req.language,
            "expected_labels": req.expected_labels,
        }
        payload.update(
            serialize_review_route_contract(
                route=ReviewRoute.PROVIDER_VISION,
                route_status=ReviewRouteStatus.EXECUTED,
                passed=verdict.passed,
            )
        )
        return payload
