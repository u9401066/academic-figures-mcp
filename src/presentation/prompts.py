"""MCP prompt definitions — reusable interaction patterns."""

from __future__ import annotations

from src.presentation.server import mcp

PromptMessage = dict[str, str]


@mcp.prompt()
def plan_figure_request(
    pmid: str,
    figure_type: str = "auto",
    style_preset: str = "journal_default",
    language: str = "zh-TW",
) -> list[PromptMessage]:
    """Reusable planning prompt for a PMID-driven academic figure request."""
    return [
        {
            "role": "user",
            "content": (
                "Plan an academic figure request with the following constraints:\n"
                f"- PMID: {pmid}\n"
                f"- Figure type: {figure_type}\n"
                f"- Style preset: {style_preset}\n"
                f"- Language: {language}\n"
                "- Resolve the best rendering route before generating.\n"
                "- Preserve citation integrity and journal-safe typography.\n"
                "- If the request is text-heavy, bilingual, or numerically exact, "
                "recommend SVG or code rendering instead of direct image generation."
            ),
        }
    ]


@mcp.prompt()
def transform_figure_request(
    target_style: str,
    preserve: str = "layout, labels, and citations",
) -> list[PromptMessage]:
    """Reusable prompt template for style conversion on an existing figure."""
    return [
        {
            "role": "user",
            "content": (
                "Transform the provided academic figure using these constraints:\n"
                f"- Target style preset: {target_style}\n"
                f"- Preserve exactly: {preserve}\n"
                "- Keep scientific meaning unchanged.\n"
                "- Keep label readability high and avoid decorative changes "
                "that reduce publication quality.\n"
                "- If the requested style reduces diagram fidelity, propose a lighter "
                "edit strategy instead of forcing a full restyle."
            ),
        }
    ]
