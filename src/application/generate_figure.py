"""Use case: generate a publication-ready figure from a planned payload."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from src.application.plan_figure import PlanFigureRequest, PlanFigureUseCase
from src.application.review_harness import (
    append_review_history,
    build_provider_review_entry,
    build_review_summary,
    run_quality_gate,
)
from src.domain.entities import GenerationManifest
from src.domain.exceptions import ValidationError

if TYPE_CHECKING:
    from src.domain.entities import GenerationResult
    from src.domain.interfaces import (
        FigureComposer,
        ImageGenerator,
        ImageVerifier,
        ManifestStore,
        MetadataFetcher,
        OutputFormatter,
        PromptBuilder,
    )


@dataclass
class GenerateFigureRequest:
    pmid: str | None = None
    source_title: str | None = None
    source_summary: str | None = None
    source_kind: str = "paper"
    source_identifier: str | None = None
    planned_payload: dict[str, Any] | None = None
    figure_type: str = "auto"
    language: str = "zh-TW"
    output_size: str = "1024x1536"
    output_format: str | None = None
    output_dir: str | None = None
    target_journal: str | None = None

    def __post_init__(self) -> None:
        self.pmid = _clean_optional_text(self.pmid)
        self.source_title = _clean_optional_text(self.source_title)
        self.source_summary = _clean_optional_text(self.source_summary)
        self.source_identifier = _clean_optional_text(self.source_identifier)
        self.output_format = _clean_optional_text(self.output_format)

        if self.planned_payload is not None:
            if not isinstance(self.planned_payload, dict) or not self.planned_payload:
                raise ValidationError("planned_payload cannot be empty")
            if (
                self.pmid is not None
                or self.source_title is not None
                or self.source_summary is not None
                or self.source_identifier is not None
                or self.source_kind != "paper"
            ):
                raise ValidationError(
                    "Provide either planned_payload or source inputs, not both"
                )
            return

        if self.pmid is None and self.source_title is None:
            raise ValidationError("Provide either pmid or source_title")
        if self.pmid is not None and self.source_title is not None:
            raise ValidationError("Provide either pmid or source_title, not both")
        if self.pmid is not None and (
            self.source_summary is not None
            or self.source_identifier is not None
            or self.source_kind != "paper"
        ):
            raise ValidationError("source_* fields are only supported when pmid is omitted")


class GenerateFigureUseCase:
    def __init__(
        self,
        fetcher: MetadataFetcher,
        generator: ImageGenerator,
        prompt_builder: PromptBuilder,
        provider_name: str = "google",
        output_dir: str = ".academic-figures/outputs",
        manifest_store: ManifestStore | None = None,
        composer: FigureComposer | None = None,
        verifier: ImageVerifier | None = None,
        output_formatter: OutputFormatter | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._generator = generator
        self._prompt_builder = prompt_builder
        self._provider_name = provider_name
        self._output_dir = output_dir
        self._manifest_store = manifest_store
        self._composer = composer
        self._verifier = verifier
        self._output_formatter = output_formatter

    def execute(self, req: GenerateFigureRequest) -> dict[str, object]:
        if req.planned_payload is not None:
            return self._execute_planned_payload(req)

        return self._execute_plan_first_bridge(req)

    def _execute_plan_first_bridge(
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
                pmid=req.pmid,
                source_title=req.source_title,
                source_summary=req.source_summary,
                source_kind=req.source_kind,
                source_identifier=req.source_identifier,
                output_format=req.output_format,
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
                output_format=req.output_format,
                output_dir=req.output_dir,
                target_journal=req.target_journal,
            )
        )
        bridged_result = dict(generated_result)
        bridged_result.update(
            {
                "pmid": plan_result.get("pmid", req.pmid),
                "source_kind": plan_result.get("source_kind", req.source_kind),
                "source_identifier": plan_result.get(
                    "source_identifier", req.source_identifier
                ),
                "title": plan_result.get("title", generated_result.get("title")),
                "journal": plan_result.get("journal"),
                "figure_type": plan_result.get(
                    "selected_figure_type",
                    generated_result.get("figure_type"),
                ),
                "template": plan_result.get("template"),
                "render_route_reason": plan_result.get("render_route_reason"),
                "generation_contract": "single_entry_plan_first",
                "warnings": self._merge_warnings(
                    plan_result.get("warnings"),
                    generated_result.get("warnings"),
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
        requested_render_route = self._as_text(payload.get("render_route")) or "image_generation"
        supported_render_routes = {
            "image_generation",
            "composite_figure",
            "layout_assemble_composite",
        }
        render_route = (
            requested_render_route
            if requested_render_route in supported_render_routes
            else "image_generation"
        )
        warnings: list[str] = []
        if requested_render_route not in supported_render_routes:
            render_route = "image_generation"
            warnings.append(
                f"render_route '{requested_render_route}' is not implemented yet; "
                "falling back to direct image generation"
            )

        language = self._as_text(payload.get("language")) or req.language
        output_size = self._as_text(payload.get("output_size")) or req.output_size
        output_format = self._normalize_output_format(
            req.output_format or self._as_text(payload.get("output_format"))
        )
        title = self._resolve_title(payload=payload, asset_kind=asset_kind)
        source_context_dict = self._as_dict(payload.get("source_context")) or {}
        payload_target_journal = self._as_text(payload.get("target_journal"))
        target_journal = req.target_journal or payload_target_journal
        source_journal = self._as_text(source_context_dict.get("journal"))
        payload_journal_profile = self._as_dict(payload.get("journal_profile"))
        journal_profile_checked = bool(payload.get("journal_profile_checked"))

        composite_result = self._execute_composite_payload(
            payload=payload,
            asset_kind=asset_kind,
            figure_type=figure_type,
            requested_render_route=requested_render_route,
            language=language,
            output_size=output_size,
            title=title,
            source_context=source_context_dict,
            target_journal=target_journal,
            warnings=warnings,
            output_dir=req.output_dir,
            output_format=output_format,
            start=start,
        )
        if composite_result is not None:
            return composite_result

        prompt_base = self._resolve_planned_prompt(
            payload=payload,
            title=title,
            asset_kind=asset_kind,
            figure_type=figure_type,
            language=language,
            output_size=output_size,
        )
        should_inject_journal = (not journal_profile_checked) or (
            req.target_journal is not None and req.target_journal != payload_target_journal
        )
        journal_profile = payload_journal_profile
        if should_inject_journal:
            prompt, journal_profile = self._prompt_builder.inject_journal_requirements(
                prompt_base,
                target_journal=target_journal,
                source_journal=source_journal,
            )
        else:
            prompt = prompt_base
        if target_journal and journal_profile is None:
            warnings.append(
                "No journal profile matched target_journal "
                f"'{target_journal}'; using generic academic defaults."
            )

        result: GenerationResult = self._generator.generate(
            prompt=prompt,
            model=self._resolve_model(payload),
        )
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

        result = self._convert_generation_result(result, output_format)

        out_dir = Path(req.output_dir or self._output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        stem = self._slugify(
            self._source_identifier(payload=payload, asset_kind=asset_kind, title=title)
        )
        out_path = out_dir / f"{stem}_{figure_type}_{ts}{result.file_extension}"
        result.save(out_path)
        expected_labels = self._as_text_list(payload.get("expected_labels"))
        quality_gate = run_quality_gate(
            self._verifier,
            result.image_bytes,
            expected_labels=expected_labels,
            figure_type=figure_type,
            language=language,
            warnings=warnings,
        )
        review_summary = build_review_summary(
            quality_gate=quality_gate,
            provider_route_available=self._verifier is not None,
        )
        review_history = append_review_history(
            [],
            build_provider_review_entry(quality_gate, source="generate_figure"),
        )
        manifest_id = self._persist_manifest(
            payload=payload,
            prompt=prompt,
            prompt_base=prompt_base,
            asset_kind=asset_kind,
            figure_type=figure_type,
            language=language,
            output_size=output_size,
            requested_render_route=requested_render_route,
            render_route=render_route,
            target_journal=target_journal,
            journal_profile=journal_profile,
            source_context=source_context_dict,
            output_path=str(out_path),
            model=result.model,
            quality_gate=quality_gate,
            review_summary=review_summary,
            review_history=review_history,
            warnings=warnings,
        )

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
            "output_format": output_format,
            "media_type": result.media_type,
            "image_size_bytes": len(result.image_bytes) if result.image_bytes else 0,
            "prompt_blocks": 7,
            "prompt_length": len(prompt),
            "elapsed_seconds": round(time.time() - start, 2),
            "gemini_text": result.text,
            "warnings": warnings,
            "manifest_id": manifest_id,
            "quality_gate": quality_gate,
            "review_summary": review_summary,
            "review_history": review_history,
        }

    def _execute_composite_payload(
        self,
        *,
        payload: dict[str, Any],
        asset_kind: str,
        figure_type: str,
        requested_render_route: str,
        language: str,
        output_size: str,
        title: str,
        source_context: dict[str, Any],
        target_journal: str | None,
        warnings: list[str],
        output_dir: str | None,
        output_format: str | None,
        start: float,
    ) -> dict[str, object] | None:
        if not self._is_composite_payload(payload, requested_render_route):
            return None
        if self._composer is None:
            warnings.append(
                f"render_route '{requested_render_route}' requested multi-panel assembly "
                "but no composer is configured; falling back to image generation"
            )
            return None

        panels = self._normalize_panels(payload.get("panels"))
        if panels is None:
            warnings.append(
                "panels must contain [image_path, label, panel_type] objects "
                "for composite assembly"
            )
            return None

        caption = self._as_text(payload.get("caption"))
        citation = self._as_text(payload.get("citation"))
        normalized_title = title or "Composite figure"
        normalized_render_route = "composite_figure"

        base_dir = Path(output_dir or self._output_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
        out_path = base_dir / f"{self._slugify(normalized_title)}_composite_{int(time.time())}.png"
        compose_result = self._composer.compose(
            panels=panels,
            title=normalized_title,
            caption=caption,
            citation=citation,
            output_path=str(out_path),
        )
        if compose_result.get("status") not in {"success", "ok"}:
            return {
                "status": "generation_failed",
                "generation_contract": "composite_render",
                "asset_kind": asset_kind,
                "title": normalized_title,
                "figure_type": figure_type,
                "render_route_requested": requested_render_route,
                "render_route_used": normalized_render_route,
                "target_journal": target_journal,
                "error": compose_result.get("error", "Composite assembly failed"),
                "warnings": warnings,
            }

        manifest_prompt = self._build_composite_prompt(
            title=normalized_title,
            panels=panels,
            caption=caption,
            citation=citation,
            language=language,
            output_size=output_size,
        )
        final_output_path = Path(str(compose_result.get("output_path") or out_path))
        final_output_path = self._convert_file(final_output_path, output_format)
        output_path = str(final_output_path)
        image_size = Path(output_path).stat().st_size if Path(output_path).exists() else 0
        media_type = self._media_type_for_output_format(output_format) or "image/png"
        expected_labels = self._as_text_list(payload.get("expected_labels"))
        image_bytes = final_output_path.read_bytes() if final_output_path.exists() else None
        quality_gate = run_quality_gate(
            self._verifier,
            image_bytes,
            expected_labels=expected_labels,
            figure_type=figure_type,
            language=language,
            warnings=warnings,
        )
        review_summary = build_review_summary(
            quality_gate=quality_gate,
            provider_route_available=self._verifier is not None,
        )
        review_history = append_review_history(
            [],
            build_provider_review_entry(quality_gate, source="generate_figure"),
        )
        manifest_id = self._persist_manifest(
            payload=payload,
            prompt=manifest_prompt,
            prompt_base=manifest_prompt,
            asset_kind=asset_kind or "multi_panel_figure",
            figure_type=figure_type or "composite",
            language=language,
            output_size=output_size,
            requested_render_route=requested_render_route,
            render_route=normalized_render_route,
            target_journal=target_journal,
            journal_profile=None,
            source_context=source_context,
            output_path=output_path,
            model="composite-assembler",
            quality_gate=quality_gate,
            review_summary=review_summary,
            review_history=review_history,
            warnings=warnings,
        )
        return {
            "status": "ok",
            "generation_contract": "composite_render",
            "asset_kind": asset_kind or "multi_panel_figure",
            "title": normalized_title,
            "figure_type": figure_type,
            "render_route_requested": requested_render_route,
            "render_route_used": normalized_render_route,
            "target_journal": target_journal,
            "journal_profile": None,
            "source_context": source_context,
            "model": "composite-assembler",
            "output_path": output_path,
            "output_format": output_format,
            "media_type": media_type,
            "image_size_bytes": image_size,
            "prompt_blocks": 1,
            "prompt_length": len(manifest_prompt),
            "elapsed_seconds": round(time.time() - start, 2),
            "warnings": warnings,
            "manifest_id": manifest_id,
            "quality_gate": quality_gate,
            "review_summary": review_summary,
            "review_history": review_history,
        }

    def _is_composite_payload(self, payload: dict[str, Any], requested_render_route: str) -> bool:
        panels = payload.get("panels")
        if isinstance(panels, list) and len(panels) > 0:
            return True
        return requested_render_route in {"composite_figure", "layout_assemble_composite"}

    def _normalize_panels(self, raw_panels: object) -> list[dict[str, str]] | None:
        if not isinstance(raw_panels, list) or not raw_panels:
            return None

        normalized: list[dict[str, str]] = []
        for index, item in enumerate(raw_panels):
            if not isinstance(item, dict):
                return None
            image_path = self._as_text(item.get("image_path")) or self._as_text(item.get("path"))
            label = self._as_text(item.get("label")) or self._default_label(index)
            panel_type = self._as_text(item.get("panel_type")) or "anatomy"
            if not image_path or not label:
                return None
            normalized.append(
                {
                    "image_path": image_path,
                    "label": label,
                    "panel_type": panel_type,
                    "prompt": self._as_text(item.get("prompt")) or "composite panel",
                }
            )
        return normalized

    @staticmethod
    def _build_composite_prompt(
        *,
        title: str,
        panels: list[dict[str, str]],
        caption: str,
        citation: str,
        language: str,
        output_size: str,
    ) -> str:
        lines = [
            f"Composite figure title: {title}",
            f"language: {language}",
            f"output_size: {output_size}",
            f"caption: {caption}" if caption else "caption: none",
            f"citation: {citation}" if citation else "citation: none",
            "panels:",
        ]
        for panel in panels:
            lines.append(
                f"- {panel.get('label')}: {panel.get('image_path')} [{panel.get('panel_type')}]"
            )
        return "\n".join(lines)

    @staticmethod
    def _default_label(index: int) -> str:
        base = ord("A") + index
        return chr(base) if 0 <= base <= ord("Z") else f"P{index + 1}"

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

    @staticmethod
    def _resolve_model(payload: dict[str, Any]) -> str | None:
        """Return a model override key if the planner recommended one."""
        rec = payload.get("model_recommendation")
        if isinstance(rec, str) and rec:
            return rec
        return None

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
            negative_constraints = self._as_text_list(prompt_pack.get("negative_constraints"))

        language_text = f"Traditional Chinese ({language})" if language == "zh-TW" else language
        block1 = f"## Block 1: TITLE & PURPOSE\ntitle: '{title}'\npurpose: {goal}"
        block2 = (
            "## Block 2: LAYOUT\n"
            f"asset_kind: {asset_kind}\n"
            f"figure_type: {figure_type}\n"
            "composition: Center-weighted icon composition with strong "
            "silhouette, readable at small sizes"
        )
        must_include_text = "; ".join(must_include) if must_include else "distinctive brand motif"
        visual_direction_text = visual_direction or "publication-grade, bold, compact, memorable"
        negative_constraints_text = (
            "; ".join(negative_constraints)
            if negative_constraints
            else "avoid clutter, avoid low-contrast details, avoid photorealistic scenes"
        )
        block3_lines = [
            "## Block 3: ELEMENTS",
            *(source_lines or ["source_context: none"]),
            f"must_include: {must_include_text}",
            (f"references: {'; '.join(references)}" if references else "references: none"),
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

    def _persist_manifest(
        self,
        *,
        payload: dict[str, Any],
        prompt: str,
        prompt_base: str,
        asset_kind: str,
        figure_type: str,
        language: str,
        output_size: str,
        requested_render_route: str,
        render_route: str,
        target_journal: str | None,
        journal_profile: dict[str, object] | None,
        source_context: dict[str, object],
        output_path: str,
        model: str,
        quality_gate: dict[str, object] | None,
        review_summary: dict[str, object],
        review_history: list[dict[str, object]],
        warnings: list[str],
    ) -> str | None:
        if self._manifest_store is None:
            return None

        parent_manifest_id: str | None = None
        parent_field = payload.get("manifest_id")
        if isinstance(parent_field, str) and parent_field.strip():
            parent_manifest_id = parent_field.strip()

        manifest: GenerationManifest = GenerationManifest(
            manifest_id=uuid4().hex,
            asset_kind=asset_kind,
            figure_type=figure_type,
            language=language,
            output_size=output_size,
            render_route_requested=requested_render_route,
            render_route_used=render_route,
            prompt=prompt,
            prompt_base=prompt_base,
            planned_payload=dict(payload),
            target_journal=target_journal,
            journal_profile=journal_profile if journal_profile is not None else None,
            source_context=source_context,
            output_path=output_path,
            model=model,
            provider=self._provider_name,
            generation_contract="planned_payload",
            quality_gate=quality_gate,
            review_summary=review_summary,
            review_history=[dict(item) for item in review_history],
            created_at=datetime.now(tz=timezone.utc),
            parent_manifest_id=parent_manifest_id,
            warnings=warnings,
        )
        self._manifest_store.save(manifest)
        return manifest.manifest_id

    def _normalize_output_format(self, value: str | None) -> str | None:
        if self._output_formatter is None:
            return _clean_optional_text(value)
        return self._output_formatter.normalize_output_format(value)

    def _media_type_for_output_format(self, output_format: str | None) -> str | None:
        if output_format is None or self._output_formatter is None:
            return None
        return self._output_formatter.media_type_for_output_format(output_format)

    def _convert_generation_result(
        self,
        result: GenerationResult,
        output_format: str | None,
    ) -> GenerationResult:
        if self._output_formatter is None:
            return result
        return self._output_formatter.convert_generation_result(result, output_format)

    def _convert_file(self, path: Path, output_format: str | None) -> Path:
        if self._output_formatter is None:
            return path
        return self._output_formatter.convert_file(path, output_format)


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
