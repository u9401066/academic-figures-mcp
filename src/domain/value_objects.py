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
