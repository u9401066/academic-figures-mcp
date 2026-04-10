"""Pure keyword-based figure type classifier.

No external dependencies — only stdlib + domain value objects.
"""

from __future__ import annotations

from typing import TypedDict

from src.domain.value_objects import ClassificationResult, FigureCategory


class _ClassificationRule(TypedDict):
    category: FigureCategory
    template: str
    keywords: tuple[str, ...]
    base_confidence: float


_RULES: list[_ClassificationRule] = [
    {
        "category": FigureCategory.FLOWCHART,
        "template": "clinical_guideline_flowchart",
        "keywords": (
            "consensus", "guideline", "algorithm", "protocol",
            "workflow", "decision tree", "practice guideline",
            "recommendation", "society guideline", "statement",
            "position paper", "care pathway", "clinical pathway",
        ),
        "base_confidence": 0.8,
    },
    {
        "category": FigureCategory.MECHANISM,
        "template": "drug_mechanism",
        "keywords": (
            "mechanism", "pathway", "signaling", "cascade",
            "pharmacology", "receptor", "binding", "interaction",
            "molecular", "synaptic", "neurotransmitter",
            "ion channel", "anesthetic", "analgesic",
        ),
        "base_confidence": 0.8,
    },
    {
        "category": FigureCategory.COMPARISON,
        "template": "trial_comparison",
        "keywords": (
            "randomized", "comparison", "versus", "vs.", "comparative",
            "non-inferiority", "superiority", "head-to-head",
            "meta-analysis", "systematic review", "network meta",
            "dose comparison", "regimen comparison",
        ),
        "base_confidence": 0.8,
    },
    {
        "category": FigureCategory.ANATOMICAL,
        "template": "anatomical_reference",
        "keywords": (
            "anatomical", "surgical technique", "approach",
            "regional anesthesia", "nerve block", "epidural",
            "spinal", "ultrasound-guided", "catheter placement",
            "airway management", "intubation", "anatomy",
        ),
        "base_confidence": 0.7,
    },
    {
        "category": FigureCategory.TIMELINE,
        "template": "timeline_evolution",
        "keywords": (
            "longitudinal", "history", "evolution", "trend",
            "temporal", "time course", "chronological",
            "over the past", "decades", "era of",
        ),
        "base_confidence": 0.7,
    },
    {
        "category": FigureCategory.STATISTICAL,
        "template": "data_visualization",
        "keywords": (
            "dose-response", "pharmacokinetic", "pk/pd",
            "population pk", "nonlinear", "monte carlo",
            "modeling", "simulation", "bayesian",
            "forest plot", "kaplan-meier", "survival",
        ),
        "base_confidence": 0.8,
    },
]


def classify_figure(
    title: str,
    abstract: str = "",
    journal: str = "",
) -> ClassificationResult:
    """Classify the best figure type from paper metadata keywords."""
    text = f"{title} {abstract} {journal}".lower()

    for rule in _RULES:
        matched = [kw for kw in rule["keywords"] if kw.lower() in text]
        if len(matched) >= 2:
            return ClassificationResult(
                figure_type=rule["category"],
                confidence=min(rule["base_confidence"] + len(matched) * 0.05, 1.0),
                reason=f"Matched keywords: {matched[:3]}",
                template_name=rule["template"],
            )
        if len(matched) == 1:
            return ClassificationResult(
                figure_type=rule["category"],
                confidence=0.5,
                reason=f"Weak match: {matched[0]}",
                template_name=rule["template"],
            )

    return ClassificationResult(
        figure_type=FigureCategory.INFOGRAPHIC,
        confidence=0.3,
        reason="No strong keywords matched, defaulting to general infographic",
        template_name="general_infographic",
    )
