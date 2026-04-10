"""
Intelligent figure type classification based on paper metadata.
Uses keyword heuristics + LLM fallback.

Figure types and their best-fit paper types:
- flowchart: consensus statements, guidelines, algorithms
- mechanism: drug mechanisms, pathways, signaling cascades
- comparison: RCTs, comparative studies, meta-analyses
- anatomical: anatomical studies, surgical techniques
- timeline: longitudinal studies, historical analyses
- statistical: dose-response, pharmacokinetics, statistical models
- infographic: general review articles, overviews
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FigureTypeResult:
    figure_type: str
    confidence: float  # 0.0 - 1.0
    reason: str
    template_name: str  # which prompt template to use


# Keyword-based classifier rules
FIGURE_RULES = [
    {
        "figure_type": "flowchart",
        "template": "clinical_guideline_flowchart",
        "keywords": [
            "consensus", "guideline", "algorithm", "protocol",
            "workflow", "decision tree", "practice guideline",
            "recommendation", "society guideline", "statement",
            "position paper", "care pathway", "clinical pathway",
        ],
        "confidence": 0.8,
    },
    {
        "figure_type": "mechanism",
        "template": "drug_mechanism",
        "keywords": [
            "mechanism", "pathway", "signaling", "cascade",
            "pharmacology", "receptor", "binding", "interaction",
            "molecular", "synaptic", "neurotransmitter",
            "ion channel", "anesthetic", "analgesic",
        ],
        "confidence": 0.8,
    },
    {
        "figure_type": "comparison",
        "template": "trial_comparison",
        "keywords": [
            "randomized", "comparison", "versus", "vs.", "comparative",
            "non-inferiority", "superiority", "head-to-head",
            "meta-analysis", "systematic review", "network meta",
            "dose comparison", "regimen comparison",
        ],
        "confidence": 0.8,
    },
    {
        "figure_type": "anatomical",
        "template": "anatomical_reference",
        "keywords": [
            "anatomical", "surgical technique", "approach",
            "regional anesthesia", "nerve block", "epidural",
            "spinal", "ultrasound-guided", "catheter placement",
            "airway management", "intubation", "anatomy",
        ],
        "confidence": 0.7,
    },
    {
        "figure_type": "timeline",
        "template": "timeline_evolution",
        "keywords": [
            "longitudinal", "history", "evolution", "trend",
            "temporal", "time course", "chronological",
            "over the past", "decades", "era of",
        ],
        "confidence": 0.7,
    },
    {
        "figure_type": "statistical",
        "template": "data_visualization",
        "keywords": [
            "dose-response", "pharmacokinetic", "pk/pd",
            "population pk", "nonlinear", "monte carlo",
            "modeling", "simulation", "bayesian",
            "forest plot", "kaplan-meier", "survival",
        ],
        "confidence": 0.8,
    },
]


def classify_figure(title: str, abstract: str = "", journal: str = "") -> FigureTypeResult:
    """Classify the best figure type based on title and abstract keywords."""
    text = f"{title} {abstract} {journal}".lower()
    
    for rule in FIGURE_RULES:
        matched = sum(1 for kw in rule["keywords"] if kw.lower() in text)
        if matched >= 2:
            return FigureTypeResult(
                figure_type=rule["figure_type"],
                confidence=min(rule["confidence"] + matched * 0.05, 1.0),
                reason=f"Matched keywords: {[kw for kw in rule['keywords'] if kw.lower() in text][:3]}",
                template_name=rule["template"],
            )
        elif matched == 1:
            return FigureTypeResult(
                figure_type=rule["figure_type"],
                confidence=0.5,
                reason=f"Weak match: {rule['keywords'][0]}",
                template_name=rule["template"],
            )
    
    # Default fallback
    return FigureTypeResult(
        figure_type="infographic",
        confidence=0.3,
        reason="No strong keywords matched, defaulting to general infographic",
        template_name="general_infographic",
    )
