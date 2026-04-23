"""Use case: plan a figure before generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.domain.classifier import classify_figure
from src.domain.entities import Paper
from src.domain.exceptions import ValidationError
from src.domain.value_objects import (
    CJK_LANGUAGES,
    EXECUTABLE_RENDER_ROUTES,
    FIGURE_TYPE_TO_TEMPLATE,
    CJKTextPolicy,
    RenderRoute,
)

if TYPE_CHECKING:
    from src.domain.interfaces import MetadataFetcher, PromptBuilder

OLLAMA_PROVIDER = "ollama"


@dataclass
class PlanFigureRequest:
    pmid: str | None = None
    source_title: str | None = None
    source_summary: str | None = None
    source_kind: str = "paper"
    source_identifier: str | None = None
    output_format: str | None = None
    figure_type: str = "auto"
    style_preset: str = "journal_default"
    language: str = "zh-TW"
    output_size: str = "1024x1536"
    target_journal: str | None = None
    expected_labels: list[str] | None = None

    def __post_init__(self) -> None:
        self.pmid = _clean_optional_text(self.pmid)
        self.source_title = _clean_optional_text(self.source_title)
        self.source_summary = _clean_optional_text(self.source_summary)
        self.source_identifier = _clean_optional_text(self.source_identifier)
        self.output_format = _clean_optional_text(self.output_format)

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
        paper = self._resolve_source(req)

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
        warnings: list[str] = []

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
            if (
                cjk_policy.recommend_pro_model
                and render_route == RenderRoute.IMAGE_GENERATION.value
            ):
                model_recommendation = "high_fidelity"
                model_reason = (
                    "CJK text with multiple labels: upgrading to Pro model for "
                    "better text rendering fidelity."
                )
            if (
                cjk_policy.recommend_vector_route
                and render_route == RenderRoute.IMAGE_GENERATION.value
            ):
                cjk_warnings.append(
                    "CJK text-heavy figure would prefer code_render_svg, but the current "
                    "generate_figure executor still runs image_generation for this route."
                )

        provider = self._provider_name
        if provider == OLLAMA_PROVIDER and render_route == RenderRoute.IMAGE_GENERATION.value:
            route_reason = (
                "Ollama local runtime fulfills the image_generation contract via "
                "structured SVG figure briefs instead of direct bitmap output."
            )
            warnings.append(
                "Switch to Google, OpenRouter, or OpenAI if you need bitmap image generation "
                "or image editing."
            )

        render_route, route_reason, route_warning = _resolve_executable_render_route(
            render_route=render_route,
            route_reason=route_reason,
        )
        if route_warning is not None:
            warnings.append(route_warning)

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
            "Preserve source traceability and citation integrity",
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

        source_reference = _source_reference(paper)
        must_include = [source_reference]
        citation = " · ".join(part for part in (paper.authors, paper.journal) if part)
        if citation:
            must_include.append(citation)

        source_context = {
            "source_kind": paper.source_kind,
            "source_identifier": paper.source_identifier,
            "pmid": paper.pmid or None,
            "title": paper.title,
            "journal": paper.journal,
        }
        planned_payload = {
            "asset_kind": _asset_kind_for_source(paper.source_kind),
            "goal": (
                f"Create a publication-ready {figure_type} visual summarizing "
                f"{source_reference}: {paper.title}"
            ),
            "title": paper.title,
            "selected_figure_type": figure_type,
            "render_route": render_route,
            "style_preset": req.style_preset,
            "language": req.language,
            "output_size": req.output_size,
            "output_format": req.output_format,
            "target_journal": req.target_journal,
            "journal_profile": journal_profile,
            "journal_profile_checked": True,
            "model_recommendation": model_recommendation,
            "expected_labels": req.expected_labels or [],
            "source_context": source_context,
            "prompt_pack": {
                "prompt": prompt_preview,
                "negative_constraints": academic_constraints,
                "source_files": [],
            },
            "must_include": must_include,
            "references": [source_reference],
        }

        return {
            "status": "ok",
            "pmid": paper.pmid or None,
            "source_kind": paper.source_kind,
            "source_identifier": paper.source_identifier,
            "title": paper.title,
            "journal": paper.journal,
            "style_preset": req.style_preset,
            "language": req.language,
            "output_size": req.output_size,
            "output_format": req.output_format,
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

    def _resolve_source(self, req: PlanFigureRequest) -> Paper:
        if req.pmid is not None:
            fetched = self._fetcher.fetch_paper(req.pmid)
            return Paper(
                pmid=fetched.pmid,
                title=fetched.title,
                authors=fetched.authors,
                journal=fetched.journal,
                pubdate=fetched.pubdate,
                abstract=fetched.abstract,
                source_kind=fetched.source_kind or "paper",
                source_identifier=fetched.source_identifier or fetched.pmid,
            )

        return Paper(
            pmid="",
            title=req.source_title or "",
            authors="",
            journal=_source_journal_label(req.source_kind),
            pubdate="",
            abstract=req.source_summary or "",
            source_kind=req.source_kind,
            source_identifier=req.source_identifier,
        )


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
        RenderRoute.IMAGE_GENERATION.value,
        (
            "Conceptual, anatomical, or mechanism-driven figures benefit "
            "from direct image generation."
        ),
    )


def _resolve_executable_render_route(
    *,
    render_route: str,
    route_reason: str,
) -> tuple[str, str, str | None]:
    if render_route in EXECUTABLE_RENDER_ROUTES:
        return render_route, route_reason, None

    fallback_route = RenderRoute.IMAGE_GENERATION.value
    warning = (
        f"Preferred render_route '{render_route}' is not executable yet; "
        f"planned payload uses '{fallback_route}' until a dedicated executor is implemented."
    )
    resolved_reason = (
        f"{route_reason} Current generate_figure execution is limited to executable routes, "
        f"so planner selected '{fallback_route}' for now."
    )
    return fallback_route, resolved_reason, warning


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


def _source_journal_label(source_kind: str) -> str:
    return {
        "paper": "Paper Brief",
        "preprint": "Preprint",
        "repo": "Code Repository",
        "brief": "User Brief",
    }.get(source_kind, source_kind.replace("_", " ").title())


def _source_reference(paper: Paper) -> str:
    if paper.pmid:
        return f"PMID {paper.pmid}"

    source_label = {
        "paper": "Paper",
        "preprint": "Preprint",
        "repo": "Repository",
        "brief": "Brief",
    }.get(paper.source_kind, paper.source_kind.replace("_", " ").title())
    if paper.source_identifier:
        return f"{source_label} {paper.source_identifier}"
    if paper.title:
        return f"{source_label}: {paper.title}"
    return f"Provided {source_label.lower()}"


def _asset_kind_for_source(source_kind: str) -> str:
    if source_kind == "repo":
        return "repository_figure"
    return "academic_figure"


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
