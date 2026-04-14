#!/usr/bin/env python3
"""
NYSORA-style composite: anatomy panel + B-mode ultrasound panel
Compositing the two Gemini panels into a publication-ready 2-panel figure.
"""

from PIL import Image, ImageDraw, ImageFont

ANATOMY = "nysora_anatomy_panel---1d08df73-a5ae-46b0-94df-79f7379386f5.jpg"
ULTRASOUND = "nysora_ultrasound_panel---bf8d5e8a-2dd2-41f9-a2d8-87d76e0e5015.jpg"
MEDIA_ROOT = "/home/eric/.openclaw/media/tool-image-generation/"
OUTPUT = "/tmp/nysora_interscalene_composite.png"

CANVAS_W, CANVAS_H = 2400, 1600
DPI = 300
MARGIN = 80
TITLE_H = 120
FOOTER_H = 120
PANEL_GAP = 30
LABELS = ["A", "B"]
TITLE = "Interscalene Brachial Plexus Block"
CAPTION = "Target: interscalene groove between anterior and middle scalene muscles"
CITATION = "PMID 41657234 · NYSORA-style Regional Anesthesia"


def load_font(size: int):
    for p in [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


# Load panel images
img_left = Image.open(MEDIA_ROOT + ANATOMY)
img_right = Image.open(MEDIA_ROOT + ULTRASOUND)

# Canvas
canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), "#FFFFFF")
draw = ImageDraw.Draw(canvas)

# Title
title_font = load_font(36)
tb = draw.textbbox((0, 0), TITLE, font=title_font)
tw = tb[2] - tb[0]
draw.text(((CANVAS_W - tw) // 2, MARGIN), TITLE, fill="#1A1A2E", font=title_font)

# Panels
panel_top = MARGIN + TITLE_H
panel_left_x = MARGIN
panel_right_x = MARGIN + (CANVAS_W - 2 * MARGIN - PANEL_GAP) // 2
panel_w = (CANVAS_W - 2 * MARGIN - PANEL_GAP) // 2
panel_h = CANVAS_H - TITLE_H - FOOTER_H - 2 * MARGIN - 40


def paste_panel(img, x):
    img_resized = img.resize((panel_w, panel_h), Image.LANCZOS)
    canvas.paste(img_resized, (x, panel_top))


paste_panel(img_left, panel_left_x)
paste_panel(img_right, panel_right_x)

# Labels
label_font = load_font(32)
for lbl, px in zip(LABELS, [panel_left_x, panel_right_x], strict=True):
    lb = draw.textbbox((0, 0), lbl, font=label_font)
    lw, lh = lb[2] - lb[0] + 20, lb[3] - lb[1] + 16
    draw.rounded_rectangle(
        [px + 10, panel_top + 10, px + 10 + lw, panel_top + 10 + lh],
        radius=8,
        fill="#FFFFFF",
        outline="#CCCCCC",
        width=1,
    )
    draw.text((px + 20, panel_top + 18), lbl, fill="#1A1A2E", font=label_font)

# Divider
div_x = panel_left_x + panel_w + PANEL_GAP // 2
draw.line([(div_x, panel_top), (div_x, panel_top + panel_h)], fill="#E0E0E0", width=2)

# Footer
footer_y = panel_top + panel_h + 40
draw.text((MARGIN, footer_y), CAPTION, fill="#555555", font=load_font(18))
draw.text((MARGIN, footer_y + 25), CITATION, fill="#888888", font=load_font(16))

# Save
canvas.save(OUTPUT, dpi=(DPI, DPI))
print(f"✅ Composite saved: {OUTPUT}")
print(f'   {CANVAS_W}x{CANVAS_H} @ {DPI} DPI = {CANVAS_W / DPI:.1f}"x{CANVAS_H / DPI:.1f}"')
