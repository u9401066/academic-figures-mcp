from __future__ import annotations

from src.domain.classifier import classify_figure
from src.domain.value_objects import FigureCategory


def test_classify_figure_returns_strong_keyword_match() -> None:
    result = classify_figure(
        title="Consensus guideline for airway rescue algorithm",
        abstract="This workflow recommendation standardizes perioperative decision tree steps.",
        journal="Journal of Testing",
    )

    assert result.figure_type is FigureCategory.FLOWCHART
    assert result.confidence > 0.8
    assert result.template_name == "clinical_guideline_flowchart"
    assert "Matched keywords" in result.reason


def test_classify_figure_falls_back_to_infographic_when_no_rules_match() -> None:
    result = classify_figure(
        title="A reflective essay on interdisciplinary collaboration",
        abstract="Narrative perspectives on teamwork and education.",
        journal="Humanities Review",
    )

    assert result.figure_type is FigureCategory.INFOGRAPHIC
    assert result.confidence == 0.3
    assert result.template_name == "general_infographic"
