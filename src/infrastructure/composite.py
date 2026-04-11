"""
Multi-panel figure composer using Pillow.

Takes individually generated panel images and composites them into a
publication-ready multi-panel figure with:
- Precise pixel-level layout control
- Auto-placed numbered labels (100% accurate text)
- Orientation markers, title, footer
- Journal-compliant spacing and typography

This implements the "分而治之" strategy:
  Gemini generates each panel → Pillow composites with perfect layout
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

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


class CompositeFigure:
    """Builds a publication-ready multi-panel figure."""

    def __init__(self, config: LayoutConfig | None = None):
        self.config = config or LayoutConfig()
        self.panels: list[dict[str, object]] = []
        self.title = ""
        self.caption = ""
        self.citation = ""

    def add_panel(self, spec: PanelSpec, image_path: str) -> CompositeFigure:
        """Add a panel image to the composition."""
        self.panels.append({"panel": spec, "image_path": image_path})
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
            title_h = bbox[3] - bbox[1] + 20
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

        # Equal-width panels with gaps
        total_gaps = (n_panels - 1) * cfg.PANEL_GAP
        panel_w = (area_right - area_left - total_gaps) // n_panels

        for i, ps in enumerate(self.panels):
            x = area_left + i * (panel_w + cfg.PANEL_GAP)
            y = panel_top
            w = panel_w
            h = panel_h

            # Load and resize panel image
            try:
                panel_img = Image.open(ps["image_path"])
                panel_img = panel_img.resize((w, h), Image.LANCZOS)
                canvas.paste(panel_img, (x, y))
            except Exception as e:
                print(f"Warning: Failed to load panel image: {e}")
                # Draw placeholder
                draw.rectangle([x, y, x + w, y + h], fill="#F0F0F0")

            # Panel label (A, B, C)
            if ps["panel"].label:
                label = ps["panel"].label
                label_font = self.get_font(cfg.LABEL_FONT_SIZE)
                self._draw_label(draw, label, x + 15, y + 15, cfg, label_font)

        # Divider lines between panels
        for i in range(n_panels - 1):
            x = area_left + (i + 1) * panel_w + i * cfg.PANEL_GAP
            draw.line(
                [(x - cfg.PANEL_GAP // 2, panel_top), (x - cfg.PANEL_GAP // 2, panel_bottom)],
                fill=cfg.DIVIDER_COLOR,
                width=cfg.DIVIDER_WIDTH,
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
            "width_inches": round(cfg.WIDTH / cfg.DPI, 1),
            "height_inches": round(cfg.HEIGHT / cfg.DPI, 1),
        }

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
