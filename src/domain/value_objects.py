"""Value objects — immutable types without identity."""

from __future__ import annotations

from dataclasses import dataclass, field
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


# ── Panel Layout Presets (Theme 2) ──────────────────────────────


class LayoutPreset(str, Enum):
    """Predefined panel arrangement strategies for composite figures."""

    GRID_2X2 = "grid_2x2"
    HORIZONTAL_STRIP = "horizontal_strip"
    VERTICAL_STRIP = "vertical_strip"
    ASYMMETRIC_LEFT = "asymmetric_left"
    SINGLE_FEATURED = "single_featured"


class PanelLabelStyle(str, Enum):
    """Labelling conventions for multi-panel figures."""

    UPPERCASE = "uppercase"
    LOWERCASE = "lowercase"
    NUMERIC = "numeric"
    ROMAN = "roman"
    NONE = "none"


LAYOUT_PRESET_CONFIGS: dict[str, dict[str, object]] = {
    LayoutPreset.GRID_2X2: {
        "columns": 2,
        "rows": 2,
        "description": "2x2 balanced grid, best for 4 panels of equal importance",
    },
    LayoutPreset.HORIZONTAL_STRIP: {
        "columns": -1,
        "rows": 1,
        "description": "Single row — all panels side-by-side, ideal for sequence or comparison",
    },
    LayoutPreset.VERTICAL_STRIP: {
        "columns": 1,
        "rows": -1,
        "description": "Single column — panels stacked top to bottom, good for step-by-step flows",
    },
    LayoutPreset.ASYMMETRIC_LEFT: {
        "columns": 2,
        "rows": -1,
        "weight_left": 0.6,
        "description": (
            "Left-weighted asymmetric — first panel occupies 60 % width, "
            "remaining panels share the right column"
        ),
    },
    LayoutPreset.SINGLE_FEATURED: {
        "columns": 1,
        "rows": -1,
        "featured_index": 0,
        "featured_height_ratio": 0.5,
        "description": (
            "One featured panel on top (50 % height), smaller panels fill the bottom row"
        ),
    },
}


def resolve_layout_preset(name: str) -> dict[str, object] | None:
    """Look up a layout preset by name.  Returns ``None`` for unknown names."""
    return LAYOUT_PRESET_CONFIGS.get(name)


# ── Poster Value Objects (Theme 3) ──────────────────────────────


class PosterSection(str, Enum):
    """Logical zones on an academic poster."""

    TITLE_BAND = "title_band"
    INTRODUCTION = "introduction"
    METHODS = "methods"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    FIGURES = "figures"
    REFERENCES = "references"


class PosterLayoutPreset(str, Enum):
    """Canvas shape presets for poster generation."""

    PORTRAIT_A0 = "portrait_a0"
    LANDSCAPE_A0 = "landscape_a0"
    TRI_COLUMN = "tri_column"


POSTER_LAYOUT_CONFIGS: dict[str, dict[str, object]] = {
    PosterLayoutPreset.PORTRAIT_A0: {
        "width_px": 3360,
        "height_px": 4752,
        "dpi": 300,
        "columns": 3,
        "description": "A0 portrait (841 x 1189 mm at 300 DPI), standard conference poster",
    },
    PosterLayoutPreset.LANDSCAPE_A0: {
        "width_px": 4752,
        "height_px": 3360,
        "dpi": 300,
        "columns": 4,
        "description": "A0 landscape (1189 x 841 mm at 300 DPI), wide-format poster",
    },
    PosterLayoutPreset.TRI_COLUMN: {
        "width_px": 3600,
        "height_px": 4800,
        "dpi": 300,
        "columns": 3,
        "description": "Three-column academic poster — balanced section widths",
    },
}


POSTER_TEXT_DENSITY_LIMITS: dict[str, int] = {
    "title_max_chars": 120,
    "section_max_chars": 800,
    "figure_caption_max_chars": 200,
    "min_font_size_pt": 24,
    "max_sections": 8,
}


# ── Style Profile Value Objects (Theme 4) ───────────────────────


@dataclass(frozen=True)
class StyleProfile:
    """Reusable visual style extracted from an existing image."""

    style_id: str
    description: str
    color_palette: list[str] = field(default_factory=list)
    typography_hints: str = ""
    layout_hints: str = ""
    mood: str = ""
    source_image_path: str = ""
    raw_extraction_text: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "style_id": self.style_id,
            "description": self.description,
            "color_palette": list(self.color_palette),
            "typography_hints": self.typography_hints,
            "layout_hints": self.layout_hints,
            "mood": self.mood,
            "source_image_path": self.source_image_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> StyleProfile:
        palette_raw = data.get("color_palette")
        palette = (
            [str(c) for c in palette_raw] if isinstance(palette_raw, list) else []
        )
        return cls(
            style_id=str(data.get("style_id") or ""),
            description=str(data.get("description") or ""),
            color_palette=palette,
            typography_hints=str(data.get("typography_hints") or ""),
            layout_hints=str(data.get("layout_hints") or ""),
            mood=str(data.get("mood") or ""),
            source_image_path=str(data.get("source_image_path") or ""),
            raw_extraction_text=str(data.get("raw_extraction_text") or ""),
        )
