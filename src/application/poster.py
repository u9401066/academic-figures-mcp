"""Use case: plan and generate an academic poster."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from src.domain.entities import GenerationManifest
from src.domain.exceptions import PosterValidationError
from src.domain.value_objects import (
    POSTER_LAYOUT_CONFIGS,
    POSTER_TEXT_DENSITY_LIMITS,
    PosterLayoutPreset,
    PosterSection,
)

if TYPE_CHECKING:
    from src.domain.entities import GenerationResult
    from src.domain.interfaces import ImageGenerator, ManifestStore, MetadataFetcher, PromptBuilder


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


@dataclass
class PlanPosterRequest:
    pmid: str
    title: str = ""
    sections: list[dict[str, str]] | None = None
    layout_preset: str = "portrait_a0"
    language: str = "zh-TW"
    target_journal: str | None = None


@dataclass
class GeneratePosterRequest:
    planned_payload: dict[str, Any] | None = None
    pmid: str | None = None
    title: str = ""
    sections: list[dict[str, str]] | None = None
    layout_preset: str = "portrait_a0"
    language: str = "zh-TW"
    output_dir: str | None = None
    target_journal: str | None = None


# ── Readability guardrails ──────────────────────────────────────


def validate_poster_content(
    title: str,
    sections: list[dict[str, str]],
) -> list[str]:
    """Return a list of guardrail warnings (empty means all checks pass)."""
    limits = POSTER_TEXT_DENSITY_LIMITS
    warnings: list[str] = []
    if len(title) > int(limits["title_max_chars"]):
        warnings.append(
            f"Title exceeds {limits['title_max_chars']} characters — "
            "consider shortening for readability at poster scale"
        )
    if len(sections) > int(limits["max_sections"]):
        warnings.append(
            f"More than {limits['max_sections']} sections — "
            "posters should be concise and scannable"
        )
    for sec in sections:
        content = sec.get("content", "")
        name = sec.get("name", "unnamed")
        if len(content) > int(limits["section_max_chars"]):
            warnings.append(
                f"Section '{name}' exceeds {limits['section_max_chars']} chars — "
                "reduce text for legibility"
            )
    return warnings


# ── Plan poster ─────────────────────────────────────────────────


class PlanPosterUseCase:
    def __init__(
        self,
        fetcher: MetadataFetcher,
        prompt_builder: PromptBuilder,
        provider_name: str,
    ) -> None:
        self._fetcher = fetcher
        self._prompt_builder = prompt_builder
        self._provider_name = provider_name

    def execute(self, req: PlanPosterRequest) -> dict[str, object]:
        paper = self._fetcher.fetch_paper(req.pmid)
        title = req.title or paper.title

        preset_name = req.layout_preset
        preset_cfg = POSTER_LAYOUT_CONFIGS.get(
            preset_name,
            POSTER_LAYOUT_CONFIGS[PosterLayoutPreset.PORTRAIT_A0],
        )

        # Build default sections from paper metadata
        sections = req.sections or _default_poster_sections(paper.abstract)

        guardrail_warnings = validate_poster_content(title, sections)
        if any("exceeds" in w for w in guardrail_warnings):
            raise PosterValidationError(
                "Poster content failed readability guardrails: "
                + "; ".join(guardrail_warnings)
            )

        section_names = [s.get("name", "unnamed") for s in sections]
        prompt = self._build_poster_prompt(
            title=title,
            sections=sections,
            language=req.language,
            layout_preset=preset_name,
            paper_meta={
                "pmid": paper.pmid,
                "authors": paper.authors,
                "journal": paper.journal,
            },
        )

        planned_payload: dict[str, object] = {
            "asset_kind": "poster",
            "goal": f"Generate a conference poster for PMID {paper.pmid}: {title}",
            "title": title,
            "layout_preset": preset_name,
            "layout_config": preset_cfg,
            "sections": sections,
            "language": req.language,
            "output_size": f"{preset_cfg.get('width_px')}x{preset_cfg.get('height_px')}",
            "target_journal": req.target_journal,
            "source_context": {
                "pmid": paper.pmid,
                "title": paper.title,
                "journal": paper.journal,
            },
            "prompt_pack": {
                "prompt": prompt,
                "negative_constraints": [
                    "Avoid dense paragraphs — use bullet points",
                    "Minimum font size 24 pt for body text",
                    "Do not exceed text density guardrails",
                ],
            },
        }

        return {
            "status": "ok",
            "pmid": paper.pmid,
            "title": title,
            "layout_preset": preset_name,
            "layout_config": preset_cfg,
            "section_names": section_names,
            "language": req.language,
            "guardrail_warnings": guardrail_warnings,
            "prompt_preview": prompt,
            "planned_payload": planned_payload,
            "next_step": {
                "tool": "generate_poster",
                "arguments": {"planned_payload": planned_payload},
            },
        }

    @staticmethod
    def _build_poster_prompt(
        *,
        title: str,
        sections: list[dict[str, str]],
        language: str,
        layout_preset: str,
        paper_meta: dict[str, str],
    ) -> str:
        lang_text = f"Traditional Chinese ({language})" if language == "zh-TW" else language
        lines = [
            "## POSTER GENERATION PROMPT",
            f"title: '{title}'",
            f"layout_preset: {layout_preset}",
            f"language: {lang_text}",
            f"PMID: {paper_meta.get('pmid', 'N/A')}",
            f"authors: {paper_meta.get('authors', 'N/A')}",
            f"journal: {paper_meta.get('journal', 'N/A')}",
            "",
            "## SECTIONS",
        ]
        for sec in sections:
            name = sec.get("name", "unnamed")
            content = sec.get("content", "")
            lines.append(f"### {name}")
            lines.append(content[:500] if content else "(empty)")
            lines.append("")
        lines.extend(
            [
                "## STYLE REQUIREMENTS",
                "- Section-aware layout with clear visual hierarchy",
                "- Title band at top with authors and affiliation",
                "- Figures placed in dedicated zones",
                "- References in footer zone",
                "- Minimum 24pt body text, 48pt section headers",
                "- High contrast, scannable from 1.5 meters",
            ]
        )
        return "\n".join(lines)


# ── Generate poster ─────────────────────────────────────────────


class GeneratePosterUseCase:
    def __init__(
        self,
        fetcher: MetadataFetcher,
        generator: ImageGenerator,
        prompt_builder: PromptBuilder,
        provider_name: str = "google",
        output_dir: str = ".academic-figures/outputs",
        manifest_store: ManifestStore | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._generator = generator
        self._prompt_builder = prompt_builder
        self._provider_name = provider_name
        self._output_dir = output_dir
        self._manifest_store = manifest_store

    def execute(self, req: GeneratePosterRequest) -> dict[str, object]:
        start = time.time()
        warnings: list[str] = []

        if req.planned_payload is not None:
            return self._execute_from_payload(req, start, warnings)

        if req.pmid is None:
            return {"status": "error", "error": "Either pmid or planned_payload is required"}

        # Bridge: plan first, then generate
        planner = PlanPosterUseCase(
            fetcher=self._fetcher,
            prompt_builder=self._prompt_builder,
            provider_name=self._provider_name,
        )
        plan = planner.execute(
            PlanPosterRequest(
                pmid=req.pmid,
                title=req.title,
                sections=req.sections,
                layout_preset=req.layout_preset,
                language=req.language,
                target_journal=req.target_journal,
            )
        )
        payload = plan.get("planned_payload")
        if not isinstance(payload, dict):
            return {"status": "error", "error": "Planning did not return planned_payload"}
        req_with_payload = GeneratePosterRequest(
            planned_payload=payload,
            language=req.language,
            output_dir=req.output_dir,
        )
        return self._execute_from_payload(req_with_payload, start, warnings)

    def _execute_from_payload(
        self,
        req: GeneratePosterRequest,
        start: float,
        warnings: list[str],
    ) -> dict[str, object]:
        payload = req.planned_payload or {}
        prompt_pack = payload.get("prompt_pack")
        prompt = ""
        if isinstance(prompt_pack, dict):
            prompt = str(prompt_pack.get("prompt", ""))
        if not prompt:
            poster_title = payload.get("title", "Untitled")
            prompt = f"Generate an academic conference poster titled: {poster_title}"

        title = str(payload.get("title", "Untitled Poster"))
        layout_preset = str(payload.get("layout_preset", "portrait_a0"))
        preset_cfg = POSTER_LAYOUT_CONFIGS.get(
            layout_preset,
            POSTER_LAYOUT_CONFIGS[PosterLayoutPreset.PORTRAIT_A0],
        )
        width_px = _safe_int(preset_cfg.get("width_px"), 3360)
        height_px = _safe_int(preset_cfg.get("height_px"), 4752)
        dpi = _safe_int(preset_cfg.get("dpi"), 300)

        # Add large-canvas export rules to prompt
        prompt += (
            f"\n\n## EXPORT RULES\n"
            f"canvas_size: {width_px}x{height_px} px at {dpi} DPI\n"
            f"layout_preset: {layout_preset}\n"
            f"columns: {preset_cfg.get('columns', 3)}"
        )

        result: GenerationResult = self._generator.generate(prompt=prompt)

        if not result.ok:
            return {
                "status": "generation_failed",
                "generation_contract": "poster",
                "title": title,
                "layout_preset": layout_preset,
                "error": result.error,
                "elapsed_seconds": round(time.time() - start, 2),
                "warnings": warnings,
            }

        out_dir = Path(req.output_dir or self._output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        slug = _slugify(title)
        out_path = out_dir / f"{slug}_poster_{ts}{result.file_extension}"
        result.save(out_path)

        manifest_id = self._persist_manifest(
            payload=payload,
            prompt=prompt,
            title=title,
            layout_preset=layout_preset,
            output_path=str(out_path),
            model=result.model,
            warnings=warnings,
        )

        return {
            "status": "ok",
            "generation_contract": "poster",
            "title": title,
            "layout_preset": layout_preset,
            "layout_config": preset_cfg,
            "output_path": str(out_path),
            "media_type": result.media_type,
            "image_size_bytes": len(result.image_bytes) if result.image_bytes else 0,
            "model": result.model,
            "prompt_length": len(prompt),
            "elapsed_seconds": round(time.time() - start, 2),
            "warnings": warnings,
            "manifest_id": manifest_id,
        }

    def _persist_manifest(
        self,
        *,
        payload: dict[str, Any],
        prompt: str,
        title: str,
        layout_preset: str,
        output_path: str,
        model: str,
        warnings: list[str],
    ) -> str | None:
        if self._manifest_store is None:
            return None

        source_context = payload.get("source_context")
        sc = dict(source_context) if isinstance(source_context, dict) else {}
        manifest = GenerationManifest(
            manifest_id=uuid4().hex,
            asset_kind="poster",
            figure_type="poster",
            language=str(payload.get("language", "en")),
            output_size=str(payload.get("output_size", "")),
            render_route_requested="poster_generation",
            render_route_used="image_generation",
            prompt=prompt,
            prompt_base=prompt,
            planned_payload=dict(payload),
            target_journal=str(payload.get("target_journal") or "") or None,
            journal_profile=None,
            source_context=sc,
            output_path=output_path,
            model=model,
            provider=self._provider_name,
            generation_contract="poster",
            warnings=warnings,
        )
        self._manifest_store.save(manifest)
        return manifest.manifest_id


def _default_poster_sections(abstract: str) -> list[dict[str, str]]:
    """Build sensible default sections from paper abstract."""
    return [
        {"name": PosterSection.INTRODUCTION.value, "content": abstract[:400] if abstract else ""},
        {"name": PosterSection.METHODS.value, "content": ""},
        {"name": PosterSection.RESULTS.value, "content": ""},
        {"name": PosterSection.CONCLUSION.value, "content": ""},
        {"name": PosterSection.REFERENCES.value, "content": ""},
    ]


def _slugify(value: str) -> str:
    """Create a filesystem-safe slug.  Keeps ASCII alphanumerics only."""
    import unicodedata

    nfkd = unicodedata.normalize("NFKD", value)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in ascii_only)
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or "poster"
