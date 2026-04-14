"""Value objects — immutable types without identity."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FigureCategory(str, Enum):
    FLOWCHART = "flowchart"
    MECHANISM = "mechanism"
    COMPARISON = "comparison"
    ANATOMICAL = "anatomical"
    TIMELINE = "timeline"
    STATISTICAL = "statistical"
    INFOGRAPHIC = "infographic"
    DATA_VISUALIZATION = "data_visualization"


class RenderRoute(str, Enum):
    IMAGE_GENERATION = "image_generation"
    IMAGE_EDIT = "image_edit"
    CODE_RENDER_MATPLOTLIB = "code_render_matplotlib"
    CODE_RENDER_D2 = "code_render_d2"
    CODE_RENDER_MERMAID = "code_render_mermaid"
    CODE_RENDER_SVG = "code_render_svg"
    LAYOUT_ASSEMBLE_SVG = "layout_assemble_svg"
    RENDER_GATEWAY_KROKI = "render_gateway_kroki"
    VECTOR_SCENE_EDIT = "vector_scene_edit"


FIGURE_TYPE_TO_TEMPLATE: dict[str, str] = {
    FigureCategory.FLOWCHART: "clinical_guideline_flowchart",
    FigureCategory.MECHANISM: "drug_mechanism",
    FigureCategory.COMPARISON: "trial_comparison",
    FigureCategory.INFOGRAPHIC: "general_infographic",
    FigureCategory.TIMELINE: "timeline_evolution",
    FigureCategory.ANATOMICAL: "anatomical_reference",
    FigureCategory.STATISTICAL: "data_chart",
    FigureCategory.DATA_VISUALIZATION: "data_chart",
}


@dataclass(frozen=True)
class ClassificationResult:
    """Result of figure type classification."""

    figure_type: FigureCategory
    confidence: float
    reason: str
    template_name: str


EVAL_DOMAINS: list[str] = [
    "text_accuracy",
    "anatomy",
    "color",
    "layout",
    "scientific_accuracy",
    "legibility",
    "visual_polish",
    "citation",
]


# ── CJK text rendering policy ──────────────────────────────

CJK_LANGUAGES = frozenset({"zh-TW", "zh-CN", "ja-JP", "ko-KR"})

#: Render-route escalation: if language is CJK and figure is text-heavy,
#: the planner should prefer deterministic rendering over bitmap generation.
TEXT_HEAVY_ROUTE_THRESHOLD = 2  # ≥2 expected labels → safer via SVG/code


@dataclass(frozen=True)
class CJKTextPolicy:
    """Encapsulates rules for non-Latin text in generated figures."""

    language: str
    expected_labels: tuple[str, ...] = ()

    @property
    def is_cjk(self) -> bool:
        return self.language in CJK_LANGUAGES

    @property
    def is_text_heavy(self) -> bool:
        return len(self.expected_labels) >= TEXT_HEAVY_ROUTE_THRESHOLD

    @property
    def needs_exact_text_block(self) -> bool:
        """True when the prompt must carry explicit CJK text constraints."""
        return self.is_cjk and len(self.expected_labels) > 0

    @property
    def recommend_pro_model(self) -> bool:
        """True when high-fidelity model is advised for text rendering."""
        return self.is_cjk and self.is_text_heavy

    @property
    def recommend_vector_route(self) -> bool:
        """True when deterministic vector rendering is safer than bitmap."""
        return self.is_cjk and self.is_text_heavy


# ── Quality gate verdict ────────────────────────────────────

QUALITY_GATE_MIN_SCORE = 3
QUALITY_GATE_MIN_TOTAL = 28  # 8 domains x 3.5 average


@dataclass(frozen=True)
class QualityVerdict:
    """Result of an automated quality gate check on a generated figure."""

    passed: bool
    domain_scores: dict[str, float]
    total_score: float
    critical_issues: tuple[str, ...]
    text_verification_passed: bool | None = None
    missing_labels: tuple[str, ...] = ()
    summary: str = ""
