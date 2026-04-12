"""MCP tool definitions — thin handlers that delegate to use cases."""

from __future__ import annotations

from src.application.edit_figure import EditFigureRequest
from src.application.evaluate_figure import EvaluateFigureRequest
from src.application.generate_figure import GenerateFigureRequest
from src.application.list_manifests import ListManifestsRequest
from src.application.plan_figure import PlanFigureRequest
from src.application.replay_manifest import ReplayManifestRequest
from src.application.retarget_journal import RetargetJournalRequest
from src.domain.exceptions import ConfigurationError, DomainError, ValidationError
from src.presentation.dependencies import Container
from src.presentation.server import mcp
from src.presentation.validation import (
    normalize_feedback,
    normalize_figure_type,
    normalize_image_path,
    normalize_language,
    normalize_list_limit,
    normalize_manifest_id,
    normalize_optional_pmid,
    normalize_output_dir,
    normalize_output_size,
    normalize_planned_payload,
    normalize_pmid,
    normalize_pmids,
    normalize_style_preset,
    normalize_target_journal,
)


def _error_payload(error: Exception, **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {"status": "error", "error": str(error)}
    payload.update(extra)
    return payload


@mcp.tool()
def plan_figure(
    pmid: str,
    figure_type: str = "auto",
    style_preset: str = "journal_default",
    language: str = "zh-TW",
    output_size: str = "1024x1536",
    target_journal: str | None = None,
) -> dict[str, object]:
    """Plan the best figure type, route, and guardrails before generation.

    This tool returns a structured plan so an MCP host can decide whether to use
    direct image generation, SVG-style rendering, or deterministic chart routes.
    """
    try:
        request = PlanFigureRequest(
            pmid=normalize_pmid(pmid),
            figure_type=normalize_figure_type(figure_type),
            style_preset=normalize_style_preset(style_preset),
            language=normalize_language(language),
            output_size=normalize_output_size(output_size),
            target_journal=normalize_target_journal(target_journal),
        )
        uc = Container.get().plan_figure_uc()
        return uc.execute(request)
    except (ConfigurationError, ValidationError, DomainError) as exc:
        return _error_payload(exc, pmid=pmid)


@mcp.tool()
def generate_figure(
    pmid: str | None = None,
    planned_payload: dict[str, object] | None = None,
    figure_type: str = "auto",
    language: str = "zh-TW",
    output_size: str = "1024x1536",
    output_dir: str | None = None,
    target_journal: str | None = None,
) -> dict[str, object]:
    """Generate a publication-ready visual asset.

    Preferred path: provide a generic planned_payload produced by planning or
    another harness layer. For backwards compatibility, callers may still pass
    a PMID directly and let the use case build the prompt internally.

    figure_type: auto | flowchart | mechanism | comparison |
                 infographic | anatomical | timeline | data_visualization
    """
    try:
        if pmid is None and planned_payload is None:
            raise ValidationError("Either pmid or planned_payload is required")
        if pmid is not None and planned_payload is not None:
            raise ValidationError("Provide either pmid or planned_payload, not both")

        request = GenerateFigureRequest(
            pmid=normalize_pmid(pmid) if pmid is not None else None,
            planned_payload=(
                normalize_planned_payload(planned_payload) if planned_payload is not None else None
            ),
            figure_type=normalize_figure_type(figure_type),
            language=normalize_language(language),
            output_size=normalize_output_size(output_size),
            output_dir=normalize_output_dir(output_dir),
            target_journal=normalize_target_journal(target_journal),
        )
        uc = Container.get().generate_figure_uc()
        return uc.execute(request)
    except (ConfigurationError, ValidationError, DomainError) as exc:
        return _error_payload(exc, pmid=pmid)


@mcp.tool()
def edit_figure(
    image_path: str,
    feedback: str,
    output_path: str | None = None,
) -> dict[str, object]:
    """Refine an academic figure using natural language feedback.

    Examples: "箭頭改紅色", "標題字大一點", "Add PMID in footer"
    """
    try:
        request = EditFigureRequest(
            image_path=normalize_image_path(image_path),
            feedback=normalize_feedback(feedback),
            output_path=(
                normalize_image_path(output_path, field_name="output_path")
                if output_path
                else None
            ),
        )
        uc = Container.get().edit_figure_uc()
        return uc.execute(request)
    except (ConfigurationError, ValidationError, DomainError) as exc:
        return _error_payload(exc)


@mcp.tool()
def evaluate_figure(
    image_path: str,
    figure_type: str = "infographic",
    reference_pmid: str | None = None,
) -> dict[str, object]:
    """Evaluate an academic figure using the 8-domain quality checklist.

    Domains: text accuracy, anatomy, color, layout,
             scientific accuracy, legibility, visual polish, citation.
    """
    try:
        request = EvaluateFigureRequest(
            image_path=normalize_image_path(image_path),
            figure_type=normalize_figure_type(figure_type, allow_auto=False),
            reference_pmid=normalize_optional_pmid(reference_pmid, field_name="reference_pmid"),
        )
        uc = Container.get().evaluate_figure_uc()
        return uc.execute(request)
    except (ConfigurationError, ValidationError, DomainError) as exc:
        return _error_payload(exc)


@mcp.tool()
def batch_generate(
    pmids: list[str],
    figure_type: str = "auto",
    language: str = "zh-TW",
    output_size: str = "1024x1536",
    output_dir: str | None = None,
) -> dict[str, object]:
    """Generate academic figures for multiple PMIDs in sequence.

    Batch mode validates the full PMID list up front and propagates language,
    output size, and output directory into every generation request.
    """
    try:
        normalized_pmids = normalize_pmids(pmids)
        normalized_figure_type = normalize_figure_type(figure_type)
        normalized_language = normalize_language(language)
        normalized_output_size = normalize_output_size(output_size)
        normalized_output_dir = normalize_output_dir(output_dir)
        uc = Container.get().batch_generate_uc()
        return uc.execute(
            pmids=normalized_pmids,
            figure_type=normalized_figure_type,
            language=normalized_language,
            output_size=normalized_output_size,
            output_dir=normalized_output_dir,
        )
    except (ConfigurationError, ValidationError, DomainError) as exc:
        return _error_payload(exc)


@mcp.tool()
def composite_figure(
    panels: list[list[str]],
    labels: list[str],
    title: str,
    caption: str = "",
    citation: str = "",
    output_path: str | None = None,
) -> dict[str, object]:
    """Composite multiple panel images into a publication-ready figure."""
    try:
        if not panels:
            raise ValidationError("panels must contain at least one item")
        if len(panels) != len(labels):
            raise ValidationError("panels and labels must be the same length")

        from src.infrastructure.composite import CompositeFigure, PanelSpec

        composer = CompositeFigure()
        for index, panel in enumerate(panels):
            if len(panel) != 2:
                raise ValidationError(f"panels[{index}] must contain [image_path, panel_type]")

            image_path = normalize_image_path(str(panel[0]), field_name=f"panels[{index}][0]")
            panel_type = str(panel[1]).strip() or "anatomy"
            label = labels[index].strip()
            if not label:
                raise ValidationError(f"labels[{index}] cannot be blank")

            composer.add_panel(
                PanelSpec(
                    prompt="composite panel",
                    label=label,
                    panel_type=panel_type,
                ),
                image_path,
            )

        composer.set_title(title.strip())
        composer.set_caption(caption.strip())
        composer.set_citation(citation.strip())
        normalized_output_path = (
            normalize_image_path(output_path, field_name="output_path") if output_path else None
        )
        return composer.compose(normalized_output_path)
    except (ConfigurationError, ValidationError, DomainError) as exc:
        return _error_payload(exc)


@mcp.tool()
def replay_manifest(
    manifest_id: str,
    output_dir: str | None = None,
) -> dict[str, object]:
    """Replay a previously saved manifest using the same prompt."""
    try:
        normalized_id = normalize_manifest_id(manifest_id)
        normalized_output_dir = normalize_output_dir(output_dir)
        uc = Container.get().replay_manifest_uc()
        return uc.execute(
            ReplayManifestRequest(
                manifest_id=normalized_id,
                output_dir=normalized_output_dir,
            )
        )
    except (ConfigurationError, ValidationError, DomainError) as exc:
        return _error_payload(exc, manifest_id=manifest_id)


@mcp.tool()
def retarget_journal(
    manifest_id: str,
    target_journal: str,
    output_dir: str | None = None,
) -> dict[str, object]:
    """Apply a new journal profile to an existing manifest and regenerate the figure."""
    try:
        normalized_id = normalize_manifest_id(manifest_id)
        normalized_target = normalize_target_journal(target_journal)
        normalized_output_dir = normalize_output_dir(output_dir)
        uc = Container.get().retarget_journal_uc()
        return uc.execute(
            RetargetJournalRequest(
                manifest_id=normalized_id,
                target_journal=normalized_target or "",
                output_dir=normalized_output_dir,
            )
        )
    except (ConfigurationError, ValidationError, DomainError) as exc:
        return _error_payload(exc, manifest_id=manifest_id, target_journal=target_journal)


@mcp.tool()
def list_manifests(limit: int = 20) -> dict[str, object]:
    """List recent manifests for replay or retargeting."""
    try:
        normalized_limit = normalize_list_limit(limit)
        uc = Container.get().list_manifests_uc()
        return uc.execute(ListManifestsRequest(limit=normalized_limit))
    except (ConfigurationError, ValidationError, DomainError) as exc:
        return _error_payload(exc, limit=limit)
