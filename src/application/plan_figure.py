"""Use case: plan a figure before generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.domain.classifier import classify_figure
from src.domain.value_objects import (
    CJK_LANGUAGES,
    FIGURE_TYPE_TO_TEMPLATE,
    CJKTextPolicy,
)

if TYPE_CHECKING:
    from src.domain.interfaces import MetadataFetcher, PromptBuilder

OLLAMA_PROVIDER = "ollama"


@dataclass
class PlanFigureRequest:
    pmid: str
    figure_type: str = "auto"
    style_preset: str = "journal_default"
    language: str = "zh-TW"
    output_size: str = "1024x1536"
    target_journal: str | None = None
    expected_labels: list[str] | None = None


class PlanFigureUseCase:
    def __init__(
        self,
        fetcher: MetadataFetcher,
        prompt_builder: PromptBuilder,
        provider_name: str,
    ) -> None:
        self._fetcher = fetcher
        self._prompt_builder = prompt_builder
        self._provider_name = provider_name

    def execute(self, req: PlanFigureRequest) -> dict[str, object]:
        paper = self._fetcher.fetch_paper(req.pmid)

        if req.figure_type == "auto":
            classification = classify_figure(
                title=paper.title,
                abstract=paper.abstract,
                journal=paper.journal,
            )
            figure_type = classification.figure_type.value
            confidence = classification.confidence
            classification_reason = classification.reason
            template_name = classification.template_name
        else:
            figure_type = req.figure_type
            confidence = 1.0
            classification_reason = "Explicit figure type provided by caller"
            template_name = FIGURE_TYPE_TO_TEMPLATE.get(figure_type, figure_type)

        render_route, route_reason = _recommend_render_route(
            title=paper.title,
            abstract=paper.abstract,
            figure_type=figure_type,
            language=req.language,
        )

        # ── CJK text policy & model escalation ─────────────
        cjk_policy = CJKTextPolicy(
            language=req.language,
            expected_labels=tuple(req.expected_labels or ()),
        )
        model_recommendation: str | None = None
        model_reason: str | None = None
        cjk_warnings: list[str] = []

        if cjk_policy.is_cjk:
            cjk_warnings.append(
                "CJK language detected — prompt includes exact-text fidelity block."
            )
            if cjk_policy.recommend_pro_model and render_route == "image_generation":
                model_recommendation = "high_fidelity"
                model_reason = (
                    "CJK text with multiple labels: upgrading to Pro model for "
                    "better text rendering fidelity."
                )
            if cjk_policy.recommend_vector_route and render_route == "image_generation":
                render_route = "code_render_svg"
                route_reason = (
                    "CJK text-heavy figure: forced to editable SVG for "
                    "reliable character rendering."
                )

        provider = self._provider_name
        warnings: list[str] = []
        if provider == OLLAMA_PROVIDER and render_route == "image_generation":
            render_route = "code_render_svg"
            route_reason = (
                "Ollama local runtime currently renders structured SVG figure briefs "
                "instead of direct bitmap image generation."
            )
            warnings.append(
                "Switch to Google or OpenRouter if you need bitmap image generation "
                "or image editing."
            )

        prompt_preview_base = self._prompt_builder.build_prompt(
            paper=paper,
            figure_type=figure_type,
            language=req.language,
            output_size=req.output_size,
            expected_labels=req.expected_labels,
        )
        prompt_preview, journal_profile = self._prompt_builder.inject_journal_requirements(
            prompt_preview_base,
            target_journal=req.target_journal,
            source_journal=paper.journal,
        )
        if req.target_journal and journal_profile is None:
            warnings.append(
                "No journal profile matched target_journal "
                f"'{req.target_journal}'; using generic academic defaults."
            )

        academic_constraints = [
            "Preserve citation integrity and PMID traceability",
            ("Prefer publication-safe typography and legibility over decorative styling"),
            ("Avoid bitmap-first rendering for numerically exact or text-heavy figures"),
        ]
        if req.language != "en":
            academic_constraints.append(
                "Review bilingual or non-English labels before publication"
            )
        if cjk_policy.is_cjk:
            academic_constraints.append(
                "Every CJK label must be rendered character-for-character — "
                "no romanization, no simplification"
            )
        if journal_profile is not None:
            journal_name = str(journal_profile.get("display_name", "selected journal"))
            academic_constraints.append(
                f"Apply {journal_name} figure requirements from the YAML registry"
            )

        must_include = [f"PMID {paper.pmid}"]
        citation = " · ".join(part for part in (paper.authors, paper.journal) if part)
        if citation:
            must_include.append(citation)

        planned_payload = {
            "asset_kind": "academic_figure",
            "goal": (
                f"Create a publication-ready {figure_type} academic figure summarizing "
                f"PMID {paper.pmid}: {paper.title}"
            ),
            "title": paper.title,
            "selected_figure_type": figure_type,
            "render_route": render_route,
            "style_preset": req.style_preset,
            "language": req.language,
            "output_size": req.output_size,
            "target_journal": req.target_journal,
            "journal_profile": journal_profile,
            "model_recommendation": model_recommendation,
            "expected_labels": req.expected_labels or [],
            "source_context": {
                "pmid": paper.pmid,
                "title": paper.title,
                "journal": paper.journal,
            },
            "prompt_pack": {
                "prompt": prompt_preview,
                "negative_constraints": academic_constraints,
                "source_files": [],
            },
            "must_include": must_include,
            "references": [f"PMID {paper.pmid}"],
        }

        return {
            "status": "ok",
            "pmid": paper.pmid,
            "title": paper.title,
            "journal": paper.journal,
            "style_preset": req.style_preset,
            "language": req.language,
            "output_size": req.output_size,
            "target_journal": req.target_journal,
            "journal_profile": journal_profile,
            "selected_figure_type": figure_type,
            "template": template_name,
            "classification_confidence": round(confidence, 2),
            "classification_reason": classification_reason,
            "render_route": render_route,
            "render_route_reason": route_reason,
            "model_recommendation": model_recommendation,
            "model_recommendation_reason": model_reason,
            "cjk_text_policy": {
                "is_cjk": cjk_policy.is_cjk,
                "expected_labels": list(cjk_policy.expected_labels),
                "recommend_pro_model": cjk_policy.recommend_pro_model,
                "recommend_vector_route": cjk_policy.recommend_vector_route,
            },
            "academic_constraints": academic_constraints,
            "warnings": warnings + cjk_warnings,
            "prompt_preview": prompt_preview,
            "planned_payload": planned_payload,
            "next_step": {
                "tool": "generate_figure",
                "arguments": {
                    "planned_payload": planned_payload,
                },
            },
        }


def _recommend_render_route(
    *,
    title: str,
    abstract: str,
    figure_type: str,
    language: str,
) -> tuple[str, str]:
    text = f"{title} {abstract}".lower()
    is_cjk = language in CJK_LANGUAGES

    if figure_type in {"data_visualization", "statistical"}:
        return (
            "code_render_matplotlib",
            (
                "Statistical and numerically exact figures should prefer "
                "deterministic chart rendering."
            ),
        )
    if figure_type in {"flowchart", "timeline"}:
        if is_cjk or language != "en" or _looks_text_heavy(text):
            return (
                "code_render_svg",
                (
                    "Structured, text-heavy diagrams (especially CJK) are safer "
                    "through editable SVG-style rendering."
                ),
            )
        return (
            "code_render_mermaid",
            "Structured decision paths map well to text-first diagram rendering.",
        )
    if figure_type == "comparison" and _needs_numeric_fidelity(text):
        return (
            "code_render_matplotlib",
            (
                "Comparative outcome figures with exact values are safer "
                "through deterministic plotting."
            ),
        )

    # CJK + text-heavy non-flowchart figures → prefer SVG over bitmap
    if is_cjk and figure_type in {"infographic", "comparison"} and _looks_text_heavy(text):
        return (
            "code_render_svg",
            (
                "CJK text-heavy infographic/comparison: routed to SVG for "
                "reliable character rendering."
            ),
        )

    return (
        "image_generation",
        (
            "Conceptual, anatomical, or mechanism-driven figures benefit "
            "from direct image generation."
        ),
    )


def _looks_text_heavy(text: str) -> bool:
    return any(
        token in text
        for token in (
            "guideline",
            "consensus",
            "recommendation",
            "statement",
            "workflow",
            "algorithm",
        )
    )


def _needs_numeric_fidelity(text: str) -> bool:
    return any(
        token in text
        for token in (
            "odds ratio",
            "hazard ratio",
            "forest plot",
            "kaplan",
            "confidence interval",
            "dose-response",
            "pk/pd",
        )
    )
