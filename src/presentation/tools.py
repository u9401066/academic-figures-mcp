"""MCP tool definitions — thin handlers that delegate to use cases."""

from __future__ import annotations

from src.application.composite_figure import CompositeFigureRequest
from src.application.contracts import serialize_exception_contract
from src.application.edit_figure import EditFigureRequest
from src.application.evaluate_figure import EvaluateFigureRequest
from src.application.generate_figure import GenerateFigureRequest
from src.application.get_manifest_detail import GetManifestDetailRequest
from src.application.list_manifests import ListManifestsRequest
from src.application.multi_turn_edit import MultiTurnEditRequest
from src.application.plan_figure import PlanFigureRequest
from src.application.prepare_publication_image import PreparePublicationImageRequest
from src.application.record_host_review import RecordHostReviewRequest
from src.application.replay_manifest import ReplayManifestRequest
from src.application.retarget_journal import RetargetJournalRequest
from src.application.verify_figure import VerifyFigureRequest
from src.domain.exceptions import ConfigurationError, DomainError, ValidationError
from src.presentation.dependencies import Container
from src.presentation.server import mcp
from src.presentation.validation import (
    normalize_expected_labels,
    normalize_feedback,
    normalize_figure_type,
    normalize_image_path,
    normalize_instructions,
    normalize_language,
    normalize_list_limit,
    normalize_manifest_id,
    normalize_optional_pmid,
    normalize_output_dir,
    normalize_output_format,
    normalize_output_size,
    normalize_plan_source,
    normalize_planned_payload,
    normalize_pmids,
    normalize_print_dimension_mm,
    normalize_publication_output_format,
    normalize_source_identifier,
    normalize_source_kind,
    normalize_source_summary,
    normalize_style_preset,
    normalize_target_dpi,
    normalize_target_journal,
)


def _error_payload(error: Exception, **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {"status": "error", "error": str(error)}
    payload.update(serialize_exception_contract(error))
    payload.update(extra)
    return payload


@mcp.tool()
def plan_figure(
    pmid: str | None = None,
    source_title: str | None = None,
    source_summary: str | None = None,
    source_kind: str = "paper",
    source_identifier: str | None = None,
    output_format: str | None = None,
    figure_type: str = "auto",
    style_preset: str = "journal_default",
    language: str = "zh-TW",
    output_size: str = "1024x1536",
    target_journal: str | None = None,
    expected_labels: list[str] | None = None,
) -> dict[str, object]:
    """Plan the best figure type, route, and guardrails before generation.

    This tool returns a structured plan so an MCP host can decide whether to use
    direct image generation, SVG-style rendering, or deterministic chart routes.

    Provide either pmid or a generic source brief. Generic planning supports
    preprints, repositories, and freeform briefs by passing source_title plus
    optional source_summary and source_identifier.

    output_format: Optional final raster delivery type such as png, gif, jpeg, or webp.
    The planner stores this preference inside planned_payload for downstream rendering.

    expected_labels: Optional list of exact text labels (especially CJK) the
    figure must contain. Enables CJK text fidelity guardrails and model escalation.
    """
    try:
        normalized_pmid, normalized_source_title = normalize_plan_source(
            pmid=pmid,
            source_title=source_title,
        )
        normalized_source_summary = normalize_source_summary(source_summary)
        normalized_source_kind = normalize_source_kind(source_kind)
        normalized_source_identifier = normalize_source_identifier(source_identifier)
        if normalized_pmid is not None and (
            normalized_source_summary is not None
            or normalized_source_identifier is not None
            or normalized_source_kind != "paper"
        ):
            raise ValidationError("source_* fields are only supported when pmid is omitted")
        request = PlanFigureRequest(
            pmid=normalized_pmid,
            source_title=normalized_source_title,
            source_summary=normalized_source_summary,
            source_kind=normalized_source_kind,
            source_identifier=normalized_source_identifier,
            output_format=normalize_output_format(output_format),
            figure_type=normalize_figure_type(figure_type),
            style_preset=normalize_style_preset(style_preset),
            language=normalize_language(language),
            output_size=normalize_output_size(output_size),
            target_journal=normalize_target_journal(target_journal),
            expected_labels=normalize_expected_labels(expected_labels),
        )
        uc = Container.get().plan_figure_uc()
        return uc.execute(request)
    except (ConfigurationError, ValidationError, DomainError) as exc:
        return _error_payload(exc, pmid=pmid, source_title=source_title)


@mcp.tool()
def generate_figure(
    pmid: str | None = None,
    source_title: str | None = None,
    source_summary: str | None = None,
    source_kind: str = "paper",
    source_identifier: str | None = None,
    planned_payload: dict[str, object] | None = None,
    figure_type: str = "auto",
    language: str = "zh-TW",
    output_size: str = "1024x1536",
    output_format: str | None = None,
    output_dir: str | None = None,
    target_journal: str | None = None,
) -> dict[str, object]:
    """Generate a publication-ready visual asset.

    Single high-level entrypoint: callers may provide planned_payload directly,
    or pass a PMID / generic source brief and let the use case plan internally
    before rendering.

    output_format: Optional final raster delivery type such as png, gif, jpeg, or webp.
    MCP applies the conversion internally after generation when possible.

    figure_type: auto | flowchart | mechanism | comparison |
                 infographic | anatomical | timeline | data_visualization
    """
    try:
        normalized_pmid: str | None = None
        normalized_source_title: str | None = None
        normalized_source_summary: str | None = None
        normalized_source_kind = "paper"
        normalized_source_identifier: str | None = None

        if planned_payload is None:
            normalized_pmid, normalized_source_title = normalize_plan_source(
                pmid=pmid,
                source_title=source_title,
            )
            normalized_source_summary = normalize_source_summary(source_summary)
            normalized_source_kind = normalize_source_kind(source_kind)
            normalized_source_identifier = normalize_source_identifier(source_identifier)
            if normalized_pmid is not None and (
                normalized_source_summary is not None
                or normalized_source_identifier is not None
                or normalized_source_kind != "paper"
            ):
                raise ValidationError("source_* fields are only supported when pmid is omitted")
        elif (
            pmid is not None
            or source_title is not None
            or source_summary is not None
            or source_identifier is not None
            or source_kind != "paper"
        ):
            raise ValidationError("Provide either planned_payload or source inputs, not both")

        request = GenerateFigureRequest(
            pmid=normalized_pmid,
            source_title=normalized_source_title,
            source_summary=normalized_source_summary,
            source_kind=normalized_source_kind,
            source_identifier=normalized_source_identifier,
            planned_payload=(
                normalize_planned_payload(planned_payload) if planned_payload is not None else None
            ),
            figure_type=normalize_figure_type(figure_type),
            language=normalize_language(language),
            output_size=normalize_output_size(output_size),
            output_format=normalize_output_format(output_format),
            output_dir=normalize_output_dir(output_dir),
            target_journal=normalize_target_journal(target_journal),
        )
        uc = Container.get().generate_figure_uc()
        return uc.execute(request)
    except (ConfigurationError, ValidationError, DomainError) as exc:
        return _error_payload(exc, pmid=pmid, source_title=source_title)


@mcp.tool()
def edit_figure(
    image_path: str,
    feedback: str,
    output_path: str | None = None,
    output_format: str | None = None,
) -> dict[str, object]:
    """Refine an academic figure using natural language feedback.

    output_format: Optional final raster delivery type such as png, gif, jpeg, or webp.

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
            output_format=normalize_output_format(output_format),
        )
        uc = Container.get().edit_figure_uc()
        return uc.execute(request)
    except (ConfigurationError, ValidationError, DomainError) as exc:
        return _error_payload(exc)


@mcp.tool()
def prepare_publication_image(
    image_path: str,
    output_path: str | None = None,
    target_dpi: int = 600,
    width_mm: float | None = None,
    height_mm: float | None = None,
    output_format: str | None = None,
    preserve_aspect_ratio: bool = True,
    allow_upscale: bool = True,
) -> dict[str, object]:
    """Resize a raster image and write publication DPI metadata using code only.

    This tool never calls image-generation providers. To truly meet 600 DPI for
    final publication size, pass width_mm and/or height_mm. Without a final print
    size it preserves pixel dimensions and writes target_dpi metadata only.

    output_format: Optional raster delivery type: png, jpeg, or tiff.
    """
    try:
        request = PreparePublicationImageRequest(
            image_path=normalize_image_path(image_path),
            output_path=(
                normalize_image_path(output_path, field_name="output_path")
                if output_path
                else None
            ),
            target_dpi=normalize_target_dpi(target_dpi),
            width_mm=normalize_print_dimension_mm(width_mm, field_name="width_mm"),
            height_mm=normalize_print_dimension_mm(height_mm, field_name="height_mm"),
            output_format=normalize_publication_output_format(output_format),
            preserve_aspect_ratio=preserve_aspect_ratio,
            allow_upscale=allow_upscale,
        )
        uc = Container.get().prepare_publication_image_uc()
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

        normalized_panels: list[dict[str, str]] = []
        for index, panel in enumerate(panels):
            if len(panel) != 2:
                raise ValidationError(f"panels[{index}] must contain [image_path, panel_type]")

            image_path = normalize_image_path(str(panel[0]), field_name=f"panels[{index}][0]")
            panel_type = str(panel[1]).strip() or "anatomy"
            label = labels[index].strip()
            if not label:
                raise ValidationError(f"labels[{index}] cannot be blank")

            normalized_panels.append(
                {
                    "prompt": "composite panel",
                    "label": label,
                    "panel_type": panel_type,
                    "image_path": image_path,
                }
            )

        normalized_output_path = (
            normalize_image_path(output_path, field_name="output_path") if output_path else None
        )
        request = CompositeFigureRequest(
            panels=normalized_panels,
            title=title.strip(),
            caption=caption.strip(),
            citation=citation.strip(),
            output_path=normalized_output_path,
        )
        uc = Container.get().composite_figure_uc()
        return uc.execute(request)
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
def record_host_review(
    manifest_id: str,
    passed: bool,
    summary: str,
    critical_issues: list[str] | None = None,
    reviewer: str = "copilot_host",
) -> dict[str, object]:
    """Record a host-side visual review back into a persisted manifest.

    Use this when Copilot or another host model inspects the generated image
    directly and needs to write its verdict back into the review harness.
    """
    try:
        normalized_critical_issues = [
            str(item).strip() for item in (critical_issues or []) if str(item).strip()
        ]
        request = RecordHostReviewRequest(
            manifest_id=normalize_manifest_id(manifest_id),
            passed=passed,
            summary=summary,
            critical_issues=normalized_critical_issues,
            reviewer=str(reviewer).strip() or "copilot_host",
        )
        uc = Container.get().record_host_review_uc()
        return uc.execute(request)
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


@mcp.tool()
def get_manifest_detail(
    manifest_id: str,
    include_lineage: bool = True,
) -> dict[str, object]:
    """Load one manifest with full review history and lineage context."""
    try:
        request = GetManifestDetailRequest(
            manifest_id=normalize_manifest_id(manifest_id),
            include_lineage=include_lineage,
        )
        uc = Container.get().get_manifest_detail_uc()
        return uc.execute(request)
    except (ConfigurationError, ValidationError, DomainError) as exc:
        return _error_payload(exc, manifest_id=manifest_id)


@mcp.tool()
def verify_figure(
    image_path: str,
    expected_labels: list[str] | None = None,
    figure_type: str = "infographic",
    language: str = "zh-TW",
) -> dict[str, object]:
    """Run the automated quality gate on a generated figure.

    Uses vision self-check to evaluate 8 quality domains and verify CJK text
    rendering accuracy. Returns pass/fail verdict, domain scores, and any
    missing or garbled labels.

    expected_labels: Exact text strings (e.g. CJK labels) the figure should contain.
    """
    try:
        request = VerifyFigureRequest(
            image_path=normalize_image_path(image_path),
            expected_labels=normalize_expected_labels(expected_labels) or [],
            figure_type=normalize_figure_type(figure_type, allow_auto=False),
            language=normalize_language(language),
        )
        uc = Container.get().verify_figure_uc()
        return uc.execute(request)
    except (ConfigurationError, ValidationError, DomainError) as exc:
        return _error_payload(exc)


@mcp.tool()
def multi_turn_edit(
    image_path: str,
    instructions: list[str],
    max_turns: int = 5,
) -> dict[str, object]:
    """Iteratively refine a figure through a multi-turn editing session.

    Sends multiple editing instructions turn-by-turn to fix CJK labels,
    adjust layout, or improve details. Each turn builds on the previous
    result for precise iterative corrections.

    instructions: List of natural language editing instructions applied in order.
    Examples: ["修正標題為「急性冠心症處置流程」", "箭頭改紅色", "加大字體"]
    """
    try:
        request = MultiTurnEditRequest(
            image_path=normalize_image_path(image_path),
            instructions=normalize_instructions(instructions),
            max_turns=max_turns,
        )
        uc = Container.get().multi_turn_edit_uc()
        return uc.execute(request)
    except (ConfigurationError, ValidationError, DomainError) as exc:
        return _error_payload(exc)
