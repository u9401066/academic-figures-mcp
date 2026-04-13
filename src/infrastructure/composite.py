"""
Multi-panel figure composer using Pillow.

Takes individually generated panel images and composites them into a
publication-ready multi-panel figure with:
- Precise pixel-level layout control
- Auto-placed numbered labels (100% accurate text)
- Orientation markers, title, footer
- Journal-compliant spacing and typography
- Layout presets (grid, strip, asymmetric, featured)

This implements the "分而治之" strategy:
  Gemini generates each panel → Pillow composites with perfect layout
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.domain.interfaces import FigureComposer
from src.domain.value_objects import (
    LAYOUT_PRESET_CONFIGS,
    LayoutPreset,
    PanelLabelStyle,
)

# ─── Type coercion helpers ──────────────────────────────────────


def _safe_int(value: object, default: int = 0) -> int:
    """Coerce a value from ``dict[str, object]`` to int safely."""
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value))
    except (ValueError, TypeError):
        return default


def _safe_float(value: object, default: float = 0.0) -> float:
    """Coerce a value from ``dict[str, object]`` to float safely."""
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (ValueError, TypeError):
        return default


# ─── Layout Config ──────────────────────────────────────────────


class LayoutConfig:
    """Publication-ready layout parameters.
    Based on Nature/Lancet journal standards.
    """

    # Canvas
    WIDTH = 2400  # px at 300 DPI ≈ 8 inches (double column: ~183mm)
    HEIGHT = 1600  # px at 300 DPI ≈ 5.33 inches
    DPI = 300

    # Margins
    MARGIN_TOP = 100
    MARGIN_BOTTOM = 80
    MARGIN_LEFT = 80
    MARGIN_RIGHT = 80
    PANEL_GAP = 40  # gap between left and right panels

    # Title area
    TITLE_SIZE = 36
    TITLE_COLOR = "#1A1A2E"

    # Panel labels (A, B, C, D etc.)
    LABEL_FONT_SIZE = 32
    LABEL_COLOR = "#1A1A2E"
    LABEL_BG_COLOR = "#FFFFFF"
    LABEL_PADDING = 10

    # Caption / footer
    FOOTER_FONT_SIZE = 18
    FOOTER_COLOR = "#555555"
    FOOTER_MARGIN_TOP = 40

    # Background
    BG_COLOR = "#FFFFFF"

    # Divider line between panels
    DIVIDER_COLOR = "#E0E0E0"
    DIVIDER_WIDTH = 2


class PanelSpec:
    """Specification for a single panel."""

    def __init__(self, prompt: str, label: str = "", panel_type: str = "anatomy"):
        self.prompt = prompt
        self.label = label  # "A", "B", "C" etc.
        self.panel_type = panel_type  # "anatomy" | "ultrasound" | "chart" | "comparison"


@dataclass
class _PanelEntry:
    panel: PanelSpec
    image_path: str


def _generate_label(index: int, style: PanelLabelStyle) -> str:
    """Generate a panel label for the given *index* and *style*."""
    if style == PanelLabelStyle.NONE:
        return ""
    if style == PanelLabelStyle.NUMERIC:
        return str(index + 1)
    if style == PanelLabelStyle.ROMAN:
        roman_numerals = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
        return roman_numerals[index] if index < len(roman_numerals) else str(index + 1)
    letter = chr(ord("A") + index) if index < 26 else f"P{index + 1}"
    if style == PanelLabelStyle.LOWERCASE:
        return letter.lower()
    return letter


def _resolve_grid(
    n_panels: int,
    preset_name: str | None,
) -> tuple[int, int]:
    """Return ``(columns, rows)`` for a given preset and panel count."""
    if preset_name and preset_name in LAYOUT_PRESET_CONFIGS:
        cfg = LAYOUT_PRESET_CONFIGS[preset_name]
        cols = _safe_int(cfg.get("columns"), -1)
        rows = _safe_int(cfg.get("rows"), -1)
        if cols > 0 and rows > 0:
            return cols, rows
        if cols > 0:
            return cols, math.ceil(n_panels / cols)
        if rows > 0:
            return math.ceil(n_panels / rows), rows
    # Auto: balanced columns
    cols = math.ceil(math.sqrt(n_panels))
    return cols, math.ceil(n_panels / cols)


class CompositeFigure:
    """Builds a publication-ready multi-panel figure."""

    def __init__(
        self,
        config: LayoutConfig | None = None,
        layout_preset: str | None = None,
        label_style: str | None = None,
    ):
        self.config = config or LayoutConfig()
        self.panels: list[_PanelEntry] = []
        self.title = ""
        self.caption = ""
        self.citation = ""
        self._layout_preset = layout_preset
        self._label_style = (
            PanelLabelStyle(label_style) if label_style else PanelLabelStyle.UPPERCASE
        )

    def add_panel(self, spec: PanelSpec, image_path: str) -> CompositeFigure:
        """Add a panel image to the composition."""
        self.panels.append(_PanelEntry(panel=spec, image_path=image_path))
        return self

    def set_title(self, title: str) -> CompositeFigure:
        self.title = title
        return self

    def set_caption(self, caption: str) -> CompositeFigure:
        self.caption = caption
        return self

    def set_citation(self, citation: str) -> CompositeFigure:
        self.citation = citation
        return self

    def get_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Load a font, with cross-platform graceful fallback."""
        font_candidates: list[str] = []

        if sys.platform == "win32":
            # Windows font paths
            font_candidates.extend(
                [
                    "C:\\Windows\\Fonts\\arial.ttf",
                    "C:\\Windows\\Fonts\\segoeui.ttf",
                    "C:\\Windows\\Fonts\\calibri.ttf",
                    "C:\\Windows\\Fonts\\verdana.ttf",
                ]
            )
        elif sys.platform == "darwin":
            # macOS font paths
            font_candidates.extend(
                [
                    "/System/Library/Fonts/Helvetica.ttc",
                    "/System/Library/Fonts/SFNSText.ttf",
                    "/Library/Fonts/Arial.ttf",
                    "/System/Library/Fonts/Supplemental/Arial.ttf",
                ]
            )

        # Linux font paths (also used as fallback on other platforms)
        font_candidates.extend(
            [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            ]
        )

        for candidate in font_candidates:
            if Path(candidate).exists():
                return ImageFont.truetype(candidate, size)
        return ImageFont.load_default()

    def compose(self, output_path: str | None = None) -> dict[str, object]:
        """Render the final composite figure."""
        cfg = self.config

        # Create canvas
        canvas = Image.new("RGB", (cfg.WIDTH, cfg.HEIGHT), cfg.BG_COLOR)
        draw = ImageDraw.Draw(canvas)

        # Calculate usable area
        area_left = cfg.MARGIN_LEFT
        area_right = cfg.WIDTH - cfg.MARGIN_RIGHT
        area_bottom = cfg.HEIGHT - cfg.MARGIN_BOTTOM

        # Title
        title_h = 0
        if self.title:
            font = self.get_font(cfg.TITLE_SIZE)
            bbox = draw.textbbox((0, 0), self.title, font=font)
            title_h = int(bbox[3] - bbox[1] + 20)
            draw.text(
                ((cfg.WIDTH - (bbox[2] - bbox[0])) // 2, cfg.MARGIN_TOP),
                self.title,
                fill=cfg.TITLE_COLOR,
                font=font,
            )

        # Panel area (below title)
        panel_top = cfg.MARGIN_TOP + title_h + 30
        panel_bottom = area_bottom - cfg.FOOTER_MARGIN_TOP - 10
        panel_h = panel_bottom - panel_top

        # Layout panels
        n_panels = len(self.panels)
        if n_panels == 0:
            return {"status": "error", "error": "No panels added"}

        # Resolve grid from preset
        cols, rows = _resolve_grid(n_panels, self._layout_preset)
        usable_w = area_right - area_left
        usable_h = panel_h

        # Check for asymmetric_left special handling
        is_asymmetric = (
            self._layout_preset == LayoutPreset.ASYMMETRIC_LEFT and n_panels >= 2
        )
        is_featured = (
            self._layout_preset == LayoutPreset.SINGLE_FEATURED and n_panels >= 2
        )

        if is_asymmetric:
            self._render_asymmetric(
                canvas, draw, area_left, panel_top, usable_w, usable_h, cfg
            )
        elif is_featured:
            self._render_featured(
                canvas, draw, area_left, panel_top, usable_w, usable_h, cfg
            )
        else:
            self._render_grid(
                canvas, draw, area_left, panel_top, usable_w, usable_h, cols, rows, cfg
            )

        # Footer / caption
        footer_y = panel_bottom + cfg.FOOTER_MARGIN_TOP
        caption = self.caption
        if self.citation:
            caption += f"\n{self.citation}"
        if caption.strip():
            footer_font = self.get_font(cfg.FOOTER_FONT_SIZE)
            draw.text(
                (cfg.MARGIN_LEFT, footer_y),
                caption.strip(),
                fill=cfg.FOOTER_COLOR,
                font=footer_font,
            )

        # Save
        if output_path is None:
            output_path = "composite_figure.png"
        canvas.save(output_path, dpi=(cfg.DPI, cfg.DPI))

        return {
            "status": "success",
            "output_path": output_path,
            "width_px": cfg.WIDTH,
            "height_px": cfg.HEIGHT,
            "dpi": cfg.DPI,
            "panels": n_panels,
            "layout_preset": self._layout_preset or "auto",
            "label_style": self._label_style.value,
            "width_inches": round(cfg.WIDTH / cfg.DPI, 1),
            "height_inches": round(cfg.HEIGHT / cfg.DPI, 1),
        }

    # ── Grid-based rendering (default + strip + grid presets) ───

    def _render_grid(
        self,
        canvas: Image.Image,
        draw: ImageDraw.ImageDraw,
        area_left: int,
        panel_top: int,
        usable_w: int,
        usable_h: int,
        cols: int,
        rows: int,
        cfg: LayoutConfig,
    ) -> None:
        panel_w = (usable_w - (cols - 1) * cfg.PANEL_GAP) // cols
        panel_h = (usable_h - (rows - 1) * cfg.PANEL_GAP) // rows

        for i, ps in enumerate(self.panels):
            col = i % cols
            row = i // cols
            x = area_left + col * (panel_w + cfg.PANEL_GAP)
            y = panel_top + row * (panel_h + cfg.PANEL_GAP)
            self._paste_panel(canvas, draw, ps, x, y, panel_w, panel_h, i, cfg)

        # Divider lines (vertical)
        for c in range(1, cols):
            x = area_left + c * panel_w + (c - 1) * cfg.PANEL_GAP + cfg.PANEL_GAP // 2
            draw.line(
                [(x, panel_top), (x, panel_top + usable_h)],
                fill=cfg.DIVIDER_COLOR,
                width=cfg.DIVIDER_WIDTH,
            )

    # ── Asymmetric left rendering ───────────────────────────────

    def _render_asymmetric(
        self,
        canvas: Image.Image,
        draw: ImageDraw.ImageDraw,
        area_left: int,
        panel_top: int,
        usable_w: int,
        usable_h: int,
        cfg: LayoutConfig,
    ) -> None:
        preset = LAYOUT_PRESET_CONFIGS.get(LayoutPreset.ASYMMETRIC_LEFT, {})
        weight_left = _safe_float(preset.get("weight_left"), 0.6)
        left_w = int(usable_w * weight_left) - cfg.PANEL_GAP // 2
        right_w = usable_w - left_w - cfg.PANEL_GAP

        # First panel — full left column
        self._paste_panel(
            canvas, draw, self.panels[0],
            area_left, panel_top, left_w, usable_h, 0, cfg,
        )

        # Remaining panels — stacked in the right column
        right_x = area_left + left_w + cfg.PANEL_GAP
        n_right = len(self.panels) - 1
        rh = (usable_h - (n_right - 1) * cfg.PANEL_GAP) // max(n_right, 1)
        for j, ps in enumerate(self.panels[1:]):
            y = panel_top + j * (rh + cfg.PANEL_GAP)
            self._paste_panel(canvas, draw, ps, right_x, y, right_w, rh, j + 1, cfg)

    # ── Single-featured rendering ───────────────────────────────

    def _render_featured(
        self,
        canvas: Image.Image,
        draw: ImageDraw.ImageDraw,
        area_left: int,
        panel_top: int,
        usable_w: int,
        usable_h: int,
        cfg: LayoutConfig,
    ) -> None:
        preset = LAYOUT_PRESET_CONFIGS.get(LayoutPreset.SINGLE_FEATURED, {})
        feat_ratio = _safe_float(preset.get("featured_height_ratio"), 0.5)
        featured_h = int(usable_h * feat_ratio) - cfg.PANEL_GAP // 2
        bottom_h = usable_h - featured_h - cfg.PANEL_GAP

        # Featured panel on top
        self._paste_panel(
            canvas, draw, self.panels[0],
            area_left, panel_top, usable_w, featured_h, 0, cfg,
        )

        # Bottom row
        n_bottom = len(self.panels) - 1
        bw = (usable_w - (n_bottom - 1) * cfg.PANEL_GAP) // max(n_bottom, 1)
        bottom_y = panel_top + featured_h + cfg.PANEL_GAP
        for j, ps in enumerate(self.panels[1:]):
            x = area_left + j * (bw + cfg.PANEL_GAP)
            self._paste_panel(canvas, draw, ps, x, bottom_y, bw, bottom_h, j + 1, cfg)

    # ── Shared helpers ──────────────────────────────────────────

    def _paste_panel(
        self,
        canvas: Image.Image,
        draw: ImageDraw.ImageDraw,
        ps: _PanelEntry,
        x: int,
        y: int,
        w: int,
        h: int,
        index: int,
        cfg: LayoutConfig,
    ) -> None:
        try:
            with Image.open(ps.image_path) as panel_image:
                resized_image = panel_image.resize((w, h), Image.Resampling.LANCZOS)
                canvas.paste(resized_image, (x, y))
        except Exception as e:
            print(f"Warning: Failed to load panel image: {e}")
            draw.rectangle([x, y, x + w, y + h], fill="#F0F0F0")

        # Panel label
        label = ps.panel.label or _generate_label(index, self._label_style)
        if label:
            label_font = self.get_font(cfg.LABEL_FONT_SIZE)
            self._draw_label(draw, label, x + 15, y + 15, cfg, label_font)

    def _draw_label(
        self,
        draw: ImageDraw.ImageDraw,
        label: str,
        x: int,
        y: int,
        cfg: LayoutConfig,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    ) -> None:
        """Draw a panel label (e.g., 'A') with a subtle background."""
        bbox = draw.textbbox((0, 0), label, font=font)
        w = (bbox[2] - bbox[0]) + cfg.LABEL_PADDING * 2
        h = (bbox[3] - bbox[1]) + cfg.LABEL_PADDING * 2
        # Background pill
        draw.rounded_rectangle(
            [x, y, x + w, y + h],
            radius=6,
            fill=cfg.LABEL_BG_COLOR,
            outline="#CCCCCC",
            width=1,
        )
        draw.text(
            (x + cfg.LABEL_PADDING, y + cfg.LABEL_PADDING),
            label,
            fill=cfg.LABEL_COLOR,
            font=font,
        )


class CompositeFigureAssembler(FigureComposer):
    """Adapter to expose CompositeFigure through the FigureComposer interface."""

    def __init__(self, config: LayoutConfig | None = None) -> None:
        self._config = config or LayoutConfig()

    def compose(
        self,
        panels: list[dict[str, str]],
        *,
        title: str,
        caption: str,
        citation: str,
        output_path: str | None = None,
        layout_preset: str | None = None,
        label_style: str | None = None,
    ) -> dict[str, object]:
        composer = CompositeFigure(
            config=self._config,
            layout_preset=layout_preset,
            label_style=label_style,
        )
        for panel in panels:
            composer.add_panel(
                PanelSpec(
                    prompt=panel.get("prompt", "composite panel"),
                    label=panel.get("label", ""),
                    panel_type=panel.get("panel_type", "anatomy"),
                ),
                panel["image_path"],
            )

        composer.set_title(title)
        composer.set_caption(caption)
        composer.set_citation(citation)
        return composer.compose(output_path)
