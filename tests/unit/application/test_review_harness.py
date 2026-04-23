from __future__ import annotations

from src.application.review_harness import (
    build_provider_review_entry,
    build_review_summary,
    run_quality_gate,
)
from src.domain.value_objects import QualityVerdict


class StubVerifier:
    def __init__(self, verdict: QualityVerdict) -> None:
        self._verdict = verdict

    def verify(self, image_bytes: bytes, **_: object) -> QualityVerdict:
        assert image_bytes == b"image"
        return self._verdict


def test_run_quality_gate_adds_typed_review_contract() -> None:
    warnings: list[str] = []
    verifier = StubVerifier(
        QualityVerdict(
            passed=False,
            domain_scores={"layout": 2.0},
            total_score=12.0,
            critical_issues=("critical layout issue",),
            text_verification_passed=False,
            missing_labels=("Label A",),
            summary="Gate failed",
        )
    )

    result = run_quality_gate(
        verifier,
        b"image",
        expected_labels=["Label A"],
        figure_type="infographic",
        language="en",
        warnings=warnings,
    )

    assert result is not None
    assert result["review_route"] == "provider_vision"
    assert result["review_status"] == "failed"
    assert warnings == [
        "Quality gate FAILED — consider using edit_figure to fix issues.",
        "Missing/garbled labels: Label A",
    ]


def test_build_review_summary_adds_route_status_contracts() -> None:
    quality_gate = {
        "passed": True,
        "summary": "All good",
        "review_route": "provider_vision",
        "review_status": "passed",
    }

    summary = build_review_summary(quality_gate=quality_gate, provider_route_available=True)

    provider_route = summary["routes"]["provider_vision"]
    host_route = summary["routes"]["host_vision"]
    assert provider_route["route"] == "provider_vision"
    assert provider_route["route_status"] == "executed"
    assert provider_route["review_status"] == "passed"
    assert provider_route["status"] == "executed"
    assert host_route["route"] == "host_vision"
    assert host_route["route_status"] == "external"
    assert host_route["review_status"] == "skipped"
    assert host_route["status"] == "external"


def test_build_provider_review_entry_adds_typed_review_fields() -> None:
    entry = build_provider_review_entry(
        {
            "passed": False,
            "summary": "Needs fixes",
            "critical_issues": ["text clash"],
            "missing_labels": [],
            "review_status": "failed",
        },
        source="generate_figure",
        reviewed_at="2026-04-15T00:00:00+00:00",
    )

    assert entry is not None
    assert entry["route"] == "provider_vision"
    assert entry["route_status"] == "recorded"
    assert entry["review_status"] == "failed"
