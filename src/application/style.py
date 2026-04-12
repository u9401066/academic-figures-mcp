"""Use cases for Theme 4: Style Intelligence and Reuse.

- ExtractStyleUseCase: analyse an image and produce a reusable StyleProfile.
- ApplyStyleUseCase: merge a stored StyleProfile into a planned_payload generation.
- ListStylesUseCase: list stored style profiles.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from src.domain.exceptions import ImageNotFoundError
from src.domain.value_objects import StyleProfile

if TYPE_CHECKING:
    from src.domain.interfaces import ImageGenerator, StyleStore


# ── Requests ────────────────────────────────────────────────────


@dataclass
class ExtractStyleRequest:
    image_path: str


@dataclass
class ApplyStyleRequest:
    style_id: str
    planned_payload: dict[str, Any]
    output_dir: str | None = None


@dataclass
class ListStylesRequest:
    limit: int = 20


# ── Extract style ───────────────────────────────────────────────


_EXTRACTION_PROMPT = (
    "Analyze the visual style of this image for reuse in future academic figures. "
    "Return a structured description covering:\n"
    "1. COLOR PALETTE — list 4-8 hex colors that dominate the image\n"
    "2. TYPOGRAPHY — font families or characteristics observed\n"
    "3. LAYOUT — overall spatial arrangement (grid, flow, radial, etc.)\n"
    "4. MOOD — the overall visual feel (clean, bold, warm, clinical, etc.)\n"
    "5. ONE-LINE DESCRIPTION — a concise summary sentence of the style\n\n"
    "Format each section with the header in CAPS followed by a colon."
)


class ExtractStyleUseCase:
    def __init__(
        self,
        generator: ImageGenerator,
        style_store: StyleStore,
    ) -> None:
        self._generator = generator
        self._style_store = style_store

    def execute(self, req: ExtractStyleRequest) -> dict[str, object]:
        img = Path(req.image_path)
        if not img.exists():
            raise ImageNotFoundError(f"Image not found: {req.image_path}")

        result = self._generator.edit(image_path=img, instruction=_EXTRACTION_PROMPT)

        raw_text = result.text or ""
        profile = _parse_style_profile(
            raw_text=raw_text,
            source_image_path=req.image_path,
        )
        self._style_store.save(profile)

        return {
            "status": "ok",
            "style_id": profile.style_id,
            "description": profile.description,
            "color_palette": profile.color_palette,
            "typography_hints": profile.typography_hints,
            "layout_hints": profile.layout_hints,
            "mood": profile.mood,
            "source_image_path": profile.source_image_path,
            "model": result.model,
            "elapsed_seconds": result.elapsed_seconds,
        }


# ── Apply style ─────────────────────────────────────────────────


class ApplyStyleUseCase:
    def __init__(
        self,
        style_store: StyleStore,
        generator: ImageGenerator,
        output_dir: str = ".academic-figures/outputs",
    ) -> None:
        self._style_store = style_store
        self._generator = generator
        self._output_dir = output_dir

    def execute(self, req: ApplyStyleRequest) -> dict[str, object]:
        start = time.time()
        loaded = self._style_store.load(req.style_id)
        if not isinstance(loaded, StyleProfile):
            return {"status": "error", "error": "Invalid style profile type"}
        profile: StyleProfile = loaded

        payload = req.planned_payload
        prompt_pack = payload.get("prompt_pack")
        base_prompt = ""
        if isinstance(prompt_pack, dict):
            base_prompt = str(prompt_pack.get("prompt", ""))
        if not base_prompt:
            base_prompt = str(payload.get("goal", "Generate an academic figure"))

        styled_prompt = _inject_style_into_prompt(base_prompt, profile)

        result = self._generator.generate(prompt=styled_prompt)
        if not result.ok:
            return {
                "status": "generation_failed",
                "generation_contract": "style_replay",
                "style_id": profile.style_id,
                "error": result.error,
                "elapsed_seconds": round(time.time() - start, 2),
            }

        out_dir = Path(req.output_dir or self._output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        out_path = out_dir / f"styled_{profile.style_id}_{ts}{result.file_extension}"
        result.save(out_path)

        return {
            "status": "ok",
            "generation_contract": "style_replay",
            "style_id": profile.style_id,
            "output_path": str(out_path),
            "media_type": result.media_type,
            "image_size_bytes": len(result.image_bytes) if result.image_bytes else 0,
            "model": result.model,
            "prompt_length": len(styled_prompt),
            "elapsed_seconds": round(time.time() - start, 2),
        }


# ── List styles ─────────────────────────────────────────────────


class ListStylesUseCase:
    def __init__(self, style_store: StyleStore) -> None:
        self._style_store = style_store

    def execute(self, req: ListStylesRequest) -> dict[str, object]:
        profiles = self._style_store.list(limit=req.limit)
        items: list[dict[str, object]] = []
        for p in profiles:
            if isinstance(p, StyleProfile):
                items.append(p.to_dict())
        return {"status": "ok", "styles": items}


# ── Helpers ─────────────────────────────────────────────────────


def _parse_style_profile(
    *,
    raw_text: str,
    source_image_path: str,
) -> StyleProfile:
    """Best-effort parsing of the LLM response into a StyleProfile."""
    style_id = uuid4().hex[:12]
    description = _extract_section(raw_text, "ONE-LINE DESCRIPTION") or "Extracted style"
    palette = _extract_hex_colors(raw_text)
    typography = _extract_section(raw_text, "TYPOGRAPHY")
    layout = _extract_section(raw_text, "LAYOUT")
    mood = _extract_section(raw_text, "MOOD")

    return StyleProfile(
        style_id=style_id,
        description=description,
        color_palette=palette,
        typography_hints=typography,
        layout_hints=layout,
        mood=mood,
        source_image_path=source_image_path,
        raw_extraction_text=raw_text,
    )


def _extract_section(text: str, header: str) -> str:
    """Pull the text following *header:* until the next header or end."""
    pattern = rf"(?i){re.escape(header)}\s*[:\-—]\s*(.+?)(?=\n[A-Za-z][A-Za-z \-]{{1,}}[:\-—]|\Z)"
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else ""


def _extract_hex_colors(text: str) -> list[str]:
    """Find unique hex colour codes in *text* (supports #RGB and #RRGGBB)."""
    matches = re.findall(r"#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?", text)
    seen: set[str] = set()
    result: list[str] = []
    for c in matches:
        # Expand 3-digit to 6-digit
        if len(c) == 4:
            c = f"#{c[1]*2}{c[2]*2}{c[3]*2}"
        upper = c.upper()
        if upper not in seen:
            seen.add(upper)
            result.append(upper)
    return result


def _inject_style_into_prompt(prompt: str, profile: StyleProfile) -> str:
    """Append a style block to an existing prompt."""
    lines = [
        "\n\n## STYLE PROFILE (reused)",
        f"style_description: {profile.description}",
    ]
    if profile.color_palette:
        lines.append(f"color_palette: {', '.join(profile.color_palette)}")
    if profile.typography_hints:
        lines.append(f"typography: {profile.typography_hints}")
    if profile.layout_hints:
        lines.append(f"layout: {profile.layout_hints}")
    if profile.mood:
        lines.append(f"mood: {profile.mood}")
    lines.append(
        "Apply the above visual style while retaining the content and structure "
        "described earlier in this prompt."
    )
    return prompt + "\n".join(lines)
