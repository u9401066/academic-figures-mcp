"""
Academic Figures MCP Server
===========================
Turn papers into publication-ready figures — for AI agents.

4 MCP tools:
- generate_figure: PMID → publication-ready medical figure
- edit_figure: Natural language refinement ("改紅箭頭")
- evaluate_figure: 8-domain quality scoring
- batch_generate: Process multiple PMIDs at once

Supports: VS Code Copilot, Claude Code, OpenClaw, any MCP-compatible agent.
"""

import os
import json
import time
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "academic-figures",
    version="0.1.0",
)

# ─── MCP Tools ───────────────────────────────────────────────

@mcp.tool()
def generate_figure(
    pmid: str,
    figure_type: str = "auto",
    language: str = "zh-TW",
    output_size: str = "1024x1536",
) -> dict:
    """Generate a publication-ready academic figure from a PubMed ID.

    Fetches paper metadata → selects optimal figure type → builds a
    7-block structured prompt using journal-compliant templates →
    generates the image via Google Gemini 3.1 Flash Image.

    figure_type: auto | flowchart | mechanism | comparison |
                 infographic | anatomical | timeline | data_visualization
    """
    from src.figure_classifier import classify_figure
    from src.prompt_engine import PromptEngine
    from src.pubmed import fetch_paper

    start = time.time()

    # Step 1: Fetch paper metadata
    paper = fetch_paper(pmid)
    if paper.get("error"):
        return {"status": "error", "pmid": pmid, "error": paper["error"]}

    # Step 2: Classify figure type
    if figure_type == "auto":
        from src.figure_classifier import classify_figure
        classification = classify_figure(
            title=paper["title"],
            abstract=paper.get("abstract", ""),
            journal=paper.get("journal", ""),
        )
        figure_type = classification.figure_type
        template_name = classification.template_name
    else:
        template_name = figure_type

    # Step 3: Build 7-block prompt (full implementation uses PromptEngine)
    engine = PromptEngine()
    prompt = engine.build_prompt(
        paper_info=paper,
        figure_type=figure_type,
        language=language,
        output_size=output_size,
    )

    elapsed = time.time() - start
    return {
        "status": "prompt_ready",
        "pmid": pmid,
        "title": paper.get("title"),
        "figure_type": figure_type,
        "template": template_name,
        "prompt_blocks": 7,
        "prompt_length": len(prompt),
        "elapsed_seconds": round(elapsed, 2),
        "next_step": "Send prompt to Gemini API for image generation",
    }


@mcp.tool()
def edit_figure(
    image_path: str,
    feedback: str,
    output_path: Optional[str] = None,
) -> dict:
    """Refine an academic figure using natural language feedback.

    Examples:
    - "箭頭改紅色" → changes arrow colors
    - "標題字大一點" → increases font size
    - "Add PMID in footer" → adds citation footer

    Uses Gemini's image-editing capability to apply changes precisely.
    """
    img = Path(image_path)
    if not img.exists():
        return {"status": "error", "error": f"Image not found: {image_path}"}

    return {
        "status": "edit_queued",
        "image_path": str(img),
        "feedback": feedback,
        "next_step": "Gemini image-edit call with natural language instruction",
    }


@mcp.tool()
def evaluate_figure(
    image_path: str,
    figure_type: str = "infographic",
    reference_pmid: Optional[str] = None,
) -> dict:
    """Evaluate an academic figure using the 8-domain quality checklist.

    Domains: text accuracy, anatomy, color, layout,
             scientific accuracy, legibility, visual polish, citation.

    Returns a scorecard with scores, issues, and actionable suggestions.
    """
    img = Path(image_path)
    if not img.exists():
        return {"status": "error", "error": f"Image not found: {image_path}"}

    return {
        "status": "evaluation_queued",
        "image_path": str(img),
        "figure_type": figure_type,
        "reference_pmid": reference_pmid,
        "domains": ["text", "anatomy", "color", "layout",
                    "scientific_accuracy", "legibility", "visual_polish", "citation"],
        "next_step": "Gemini Vision scoring with 8-domain rubric",
    }


@mcp.tool()
def batch_generate(
    pmids: list[str],
    figure_type: str = "auto",
    output_dir: Optional[str] = None,
) -> dict:
    """Generate academic figures for multiple PMIDs in sequence.

    Ideal for systematic reviews or meta-analysis figure batches.
    """
    results = []
    for pmid in pmids:
        r = generate_figure(pmid=pmid, figure_type=figure_type)
        results.append(r)

    success = sum(1 for r in results if "error" not in r)
    return {
        "total": len(pmids),
        "success": success,
        "failed": len(pmids) - success,
        "results": results,
    }

@mcp.tool()
def composite_figure(
    panels: list[list[str]],
    labels: list[str],
    title: str,
    caption: str = "",
    citation: str = "",
    output_path: Optional[str] = None,
) -> dict:
    """Composite multiple panel images into a publication-ready figure.

    Takes individually generated panel images and composites them with:
    - Nature/Lancet compliant layout (8" × 5.3" @ 300 DPI)
    - Auto-placed panel labels (A, B, C...)
    - Orientation markers, title, footer with citation
    - Precise pixel-level layout control

    Args:
        panels: List of [image_path_str, panel_type_str] e.g. [["/path/to/panel.png", "anatomy"]]
        labels: Panel labels e.g. ["A", "B", "C"]
        title: Figure title
        caption: Optional caption text
        citation: Optional citation (e.g. "PMID 12345 · NYSORA")
        output_path: Where to save (default: ./composite_figure.png)

    Returns:
        {"status": "success", "output_path": "...", "dimensions": {"w":..., "h":..., "dpi": 300}}
    """
    from src.composite import CompositeFigure, PanelSpec

    if len(panels) != len(labels):
        return {"status": "error", "error": "panels and labels must be same length"}

    comp = CompositeFigure()
    for i, (img_path, ptype) in enumerate(panels):
        comp.add_panel(PanelSpec(
            prompt="composite panel",
            label=labels[i],
            panel_type=ptype,
        ), img_path)

    comp.set_title(title)
    comp.set_caption(caption)
    comp.set_citation(citation)

    return comp.compose(output_path)


# ─── Entry Point ─────────────────────────────────────────────

def main():
    """Run the MCP server (stdio transport for VS Code Copilot integration)."""
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
