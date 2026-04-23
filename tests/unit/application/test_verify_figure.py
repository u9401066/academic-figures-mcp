from __future__ import annotations

from typing import TYPE_CHECKING

from src.application.verify_figure import VerifyFigureRequest, VerifyFigureUseCase
from src.domain.value_objects import QualityVerdict

if TYPE_CHECKING:
    from pathlib import Path


class StubVerifier:
    def __init__(self, verdict: QualityVerdict) -> None:
        self._verdict = verdict
        self.calls: list[tuple[bytes, list[str], str, str]] = []

    def verify(
        self,
        image_bytes: bytes,
        *,
        expected_labels: list[str],
        figure_type: str,
        language: str,
    ) -> QualityVerdict:
        self.calls.append((image_bytes, expected_labels, figure_type, language))
        return self._verdict


def test_verify_figure_serializes_typed_review_metadata(tmp_path: Path) -> None:
    image_path = tmp_path / "figure.png"
    image_path.write_bytes(b"figure-bytes")
    verifier = StubVerifier(
        QualityVerdict(
            passed=True,
            domain_scores={"layout": 4.0},
            total_score=32.0,
            critical_issues=(),
            text_verification_passed=True,
            missing_labels=(),
            summary="Looks good",
        )
    )
    use_case = VerifyFigureUseCase(verifier=verifier)

    result = use_case.execute(
        VerifyFigureRequest(
            image_path=str(image_path),
            expected_labels=["Label A"],
            figure_type="infographic",
            language="en",
        )
    )

    assert result["status"] == "ok"
    assert result["review_route"] == "provider_vision"
    assert result["route_status"] == "executed"
    assert result["review_status"] == "passed"
    assert verifier.calls == [(b"figure-bytes", ["Label A"], "infographic", "en")]
