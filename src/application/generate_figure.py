"""Use case: generate a publication-ready figure from a planned payload."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.application.plan_figure import PlanFigureRequest, PlanFigureUseCase

if TYPE_CHECKING:
    from src.domain.entities import GenerationResult
    from src.domain.interfaces import ImageGenerator, MetadataFetcher, PromptBuilder


PMID_COMPATIBILITY_WARNING = (
    "PMID input used the internal plan-first compatibility bridge. "
    "Prefer plan_figure followed by generate_figure(planned_payload)."
)


@dataclass
class GenerateFigureRequest:
    pmid: str | None = None
    planned_payload: dict[str, Any] | None = None
    figure_type: str = "auto"
    language: str = "zh-TW"
    output_size: str = "1024x1536"
    output_dir: str | None = None
    target_journal: str | None = None


class GenerateFigureUseCase:
    def __init__(
        self,
        fetcher: MetadataFetcher,
        generator: ImageGenerator,
        prompt_builder: PromptBuilder,
        provider_name: str = "google",
        output_dir: str = ".academic-figures/outputs",
    ) -> None:
        self._fetcher = fetcher
        self._generator = generator
        self._prompt_builder = prompt_builder
        self._provider_name = provider_name
        self._output_dir = output_dir

    def execute(self, req: GenerateFigureRequest) -> dict[str, object]:
        if req.planned_payload is not None:
            return self._execute_planned_payload(req)
        if req.pmid is None:
            return {
                "status": "error",
                "error": "Either pmid or planned_payload is required",
            }

        return self._execute_pmid_compatibility_bridge(req)

    def _execute_pmid_compatibility_bridge(
        self,
        req: GenerateFigureRequest,
    ) -> dict[str, object]:
        planner = PlanFigureUseCase(
            fetcher=self._fetcher,
            prompt_builder=self._prompt_builder,
            provider_name=self._provider_name,
        )
        plan_result = planner.execute(
            PlanFigureRequest(
                pmid=req.pmid or "",
                figure_type=req.figure_type,
                language=req.language,
                output_size=req.output_size,
                target_journal=req.target_journal,
            )
        )
        payload = self._as_dict(plan_result.get("planned_payload"))
        if payload is None:
            return {
                "status": "error",
                "error": "Planning step did not return planned_payload",
                "pmid": req.pmid,
            }

        generated_result = self._execute_planned_payload(
            GenerateFigureRequest(
                planned_payload=payload,
                figure_type=req.figure_type,
                language=req.language,
                output_size=req.output_size,
                output_dir=req.output_dir,
                target_journal=req.target_journal,
            )
        )
        bridged_result = dict(generated_result)
        bridged_result.update(
            {
                "pmid": plan_result.get("pmid", req.pmid),
                "title": plan_result.get("title", generated_result.get("title")),
                "journal": plan_result.get("journal"),
                "figure_type": plan_result.get(
                    "selected_figure_type",
                    generated_result.get("figure_type"),
                ),
                "template": plan_result.get("template"),
                "render_route_reason": plan_result.get("render_route_reason"),
                "generation_contract": "pmid_compatibility_bridge",
                "warnings": self._merge_warnings(
                    plan_result.get("warnings"),
                    generated_result.get("warnings"),
                    [PMID_COMPATIBILITY_WARNING],
                ),
            }
        )
        return bridged_result

    def _execute_planned_payload(self, req: GenerateFigureRequest) -> dict[str, object]:
        start = time.time()
        payload = req.planned_payload or {}

        asset_kind = self._as_text(payload.get("asset_kind")) or "generic_visual"
        figure_type = (
            self._as_text(payload.get("selected_figure_type"))
            or self._as_text(payload.get("figure_type"))
            or (req.figure_type if req.figure_type != "auto" else "infographic")
        )
        requested_render_route = (
            self._as_text(payload.get("render_route")) or "image_generation"
        )
        render_route = requested_render_route
        warnings: list[str] = []
        if requested_render_route != "image_generation":
            render_route = "image_generation"
            warnings.append(
                f"render_route '{requested_render_route}' is not implemented yet; "
                "falling back to direct image generation"
            )

        language = self._as_text(payload.get("language")) or req.language
        output_size = self._as_text(payload.get("output_size")) or req.output_size
        title = self._resolve_title(payload=payload, asset_kind=asset_kind)
        prompt = self._resolve_planned_prompt(
            payload=payload,
            title=title,
            asset_kind=asset_kind,
            figure_type=figure_type,
            language=language,
            output_size=output_size,
        )
        source_context_dict = self._as_dict(payload.get("source_context")) or {}
        payload_target_journal = self._as_text(payload.get("target_journal"))
        target_journal = req.target_journal or payload_target_journal
        source_journal = self._as_text(source_context_dict.get("journal"))
        payload_journal_profile = self._as_dict(payload.get("journal_profile"))
        should_inject_journal = payload_journal_profile is None or (
            req.target_journal is not None
            and req.target_journal != payload_target_journal
        )
        journal_profile = payload_journal_profile
        if should_inject_journal:
            prompt, journal_profile = self._prompt_builder.inject_journal_requirements(
                prompt,
                target_journal=target_journal,
                source_journal=source_journal,
            )
        if target_journal and journal_profile is None:
            warnings.append(
                "No journal profile matched target_journal "
                f"'{target_journal}'; using generic academic defaults."
            )

        result: GenerationResult = self._generator.generate(prompt=prompt)
        if not result.ok:
            return {
                "status": "generation_failed",
                "generation_contract": "planned_payload",
                "asset_kind": asset_kind,
                "title": title,
                "figure_type": figure_type,
                "render_route_requested": requested_render_route,
                "render_route_used": render_route,
                "model": result.model,
                "error": result.error,
                "elapsed_seconds": result.elapsed_seconds,
                "journal_profile": journal_profile,
                "warnings": warnings,
            }

        out_dir = Path(req.output_dir or self._output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        stem = self._slugify(
            self._source_identifier(payload=payload, asset_kind=asset_kind, title=title)
        )
        out_path = out_dir / f"{stem}_{figure_type}_{ts}{result.file_extension}"
        result.save(out_path)

        return {
            "status": "ok",
            "generation_contract": "planned_payload",
            "asset_kind": asset_kind,
            "title": title,
            "figure_type": figure_type,
            "render_route_requested": requested_render_route,
            "render_route_used": render_route,
            "target_journal": target_journal,
            "journal_profile": journal_profile,
            "source_context": source_context_dict,
            "model": result.model,
            "output_path": str(out_path),
            "media_type": result.media_type,
            "image_size_bytes": len(result.image_bytes) if result.image_bytes else 0,
            "prompt_blocks": 7,
            "prompt_length": len(prompt),
            "elapsed_seconds": round(time.time() - start, 2),
            "gemini_text": result.text,
            "warnings": warnings,
        }

    def _resolve_title(self, *, payload: dict[str, Any], asset_kind: str) -> str:
        source_context = payload.get("source_context")
        if isinstance(source_context, dict):
            title = self._as_text(source_context.get("title"))
            if title:
                return title
        title = self._as_text(payload.get("title"))
        if title:
            return title
        return asset_kind.replace("_", " ").title()

    def _resolve_planned_prompt(
        self,
        *,
        payload: dict[str, Any],
        title: str,
        asset_kind: str,
        figure_type: str,
        language: str,
        output_size: str,
    ) -> str:
        prompt_pack = payload.get("prompt_pack")
        if isinstance(prompt_pack, dict):
            packed_prompt = self._as_text(prompt_pack.get("prompt"))
            if packed_prompt:
                return packed_prompt

        goal = (
            self._as_text(payload.get("goal"))
            or f"Create a distinctive {asset_kind.replace('_', ' ')} for {title}."
        )
        style_preset = self._as_text(payload.get("style_preset")) or "custom"
        visual_direction = self._as_text(payload.get("visual_direction"))
        source_context = payload.get("source_context")
        source_lines: list[str] = []
        if isinstance(source_context, dict):
            for key in ("pmid", "title", "journal", "repo", "tagline", "summary"):
                value = self._as_text(source_context.get(key))
                if value:
                    source_lines.append(f"{key}: {value}")

        must_include = self._as_text_list(payload.get("must_include"))
        references = self._as_text_list(payload.get("references"))
        negative_constraints = []
        if isinstance(prompt_pack, dict):
            negative_constraints = self._as_text_list(
                prompt_pack.get("negative_constraints")
            )

        language_text = (
            f"Traditional Chinese ({language})" if language == "zh-TW" else language
        )
        block1 = (
            "## Block 1: TITLE & PURPOSE\n"
            f"title: '{title}'\n"
            f"purpose: {goal}"
        )
        block2 = (
            "## Block 2: LAYOUT\n"
            f"asset_kind: {asset_kind}\n"
            f"figure_type: {figure_type}\n"
            "composition: Center-weighted icon composition with strong "
            "silhouette, readable at small sizes"
        )
        must_include_text = "; ".join(must_include) if must_include else "distinctive brand motif"
        visual_direction_text = (
            visual_direction or "publication-grade, bold, compact, memorable"
        )
        negative_constraints_text = (
            "; ".join(negative_constraints)
            if negative_constraints
            else "avoid clutter, avoid low-contrast details, avoid photorealistic scenes"
        )
        block3_lines = [
            "## Block 3: ELEMENTS",
            *(source_lines or ["source_context: none"]),
            f"must_include: {must_include_text}",
            (
                f"references: {'; '.join(references)}"
                if references
                else "references: none"
            ),
        ]
        block3 = "\n".join(block3_lines)
        block4 = (
            "## Block 4: COLOR\n"
            "palette: deep academic navy, teal, and warm amber\n"
            f"style_preset: {style_preset}\n"
            f"visual_direction: {visual_direction_text}"
        )
        block5 = (
            "## Block 5: TEXT\n"
            f"language: {language_text}\n"
            "text_usage: minimal, avoid tiny labels, prioritize symbolic "
            "communication"
        )
        block6 = (
            "## Block 6: STYLE\n"
            "style: premium scientific product icon, modern, crisp, "
            "high-contrast, no mockup frame\n"
            f"negative_constraints: {negative_constraints_text}"
        )
        block7 = f"## Block 7: SIZE\ncanvas: {output_size}"
        return "\n\n".join([block1, block2, block3, block4, block5, block6, block7])

    @staticmethod
    def _as_text(value: object) -> str:
        return value.strip() if isinstance(value, str) else ""

    @staticmethod
    def _as_dict(value: object) -> dict[str, object] | None:
        if not isinstance(value, dict):
            return None
        return dict(value)

    @classmethod
    def _as_text_list(cls, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        items = []
        for item in value:
            text = cls._as_text(item)
            if text:
                items.append(text)
        return items

    @classmethod
    def _merge_warnings(cls, *sources: object) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for source in sources:
            for warning in cls._as_text_list(source):
                if warning in seen:
                    continue
                merged.append(warning)
                seen.add(warning)
        return merged

    def _source_identifier(
        self,
        *,
        payload: dict[str, Any],
        asset_kind: str,
        title: str,
    ) -> str:
        source_context = payload.get("source_context")
        if isinstance(source_context, dict):
            pmid = self._as_text(source_context.get("pmid"))
            if pmid:
                return pmid
            repo = self._as_text(source_context.get("repo"))
            if repo:
                return repo
        return title or asset_kind

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", value.lower())
        slug = slug.strip("_")
        return slug or "asset"
