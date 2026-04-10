"""
OpenClaw Illustrator MCP Server
A medical figure generation tool for VS Code Copilot users.

Usage: pip install -e .  →  then add MCP config to VS Code Copilot
"""

import json
import asyncio
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("openclaw-illustrator")

# ──────────────────────────────────────────────────────────────
# 4 MCP Tools — Copilot sees these as function calls
# ──────────────────────────────────────────────────────────────

@mcp.tool()
async def generate_figure(
    pmid: str,
    figure_type: str = "auto",
    language: str = "zh-TW",
    output_size: str = "1024x1536",
) -> dict:
    """Generate a medical academic figure from a paper (by PMID).
    
    This uses a LLM-powered orchestrator to:
    1. Fetch paper metadata & abstract from PubMed
    2. Auto-select the best figure type (flowchart/mechanism/comparison/etc.)
    3. Build a 7-block structured prompt using journal standards
    4. Generate the image using Google Gemini 3.1 Flash Image
    5. Auto-evaluate quality and retry if needed
    
    Args:
        pmid: PubMed ID of the paper (e.g., "41657234")
        figure_type: One of: flowchart, mechanism, comparison, 
                     infographic, anatomical, timeline, statistical, auto
        language: Output language — zh-TW, en
        output_size: Image resolution (default 1024x1536 for portrait)
    
    Returns:
        {
            "status": "success" | "error",
            "image_path": "/path/to/generated.png",
            "figure_type": "flowchart",
            "pmid": "41657234",
            "title": "Paper title...",
            "quality_scores": { "anatomy": 8, "text": 7, ... },
            "retry_count": 0
        }
    """
    from src.orchestrator import run_generate_pipeline
    
    return await run_generate_pipeline(
        pmid=pmid,
        figure_type=figure_type,
        language=language,
        output_size=output_size,
    )


@mcp.tool()
async def edit_figure(
    image_path: str,
    feedback: str,
    max_retries: int = 2,
) -> dict:
    """Iteratively refine a generated medical figure using natural language feedback.
    
    The AI reads your feedback (e.g., "箭頭改紅色", "標題字大一點），
    translates it into a Gemini image edit prompt, and re-renders the figure.
    
    Args:
        image_path: Path to the current figure image
        feedback: Natural language instruction (Chinese or English OK)
        max_retries: Maximum number of retry attempts (default 2)
    
    Returns:
        {
            "status": "success" | "error",
            "image_path": "/path/to/updated.png",
            "applied_changes": ["Changed arrow color to red", ...],
            "quality_scores": { ... },
            "retry_count": 1
        }
    """
    from src.orchestrator import run_edit_pipeline
    
    return await run_edit_pipeline(
        image_path=image_path,
        feedback=feedback,
        max_retries=max_retries,
    )


@mcp.tool()
async def evaluate_figure(
    image_path: str,
    figure_type: str = "infographic",
) -> dict:
    """Evaluate a generated medical figure using the 8-domain quality checklist.
    
    Returns scores for each domain and actionable suggestions for improvement.
    
    Args:
        image_path: Path to the figure image
        figure_type: Type of figure (for type-specific evaluation criteria)
    
    Returns:
        {
            "overall_score": 7.5,
            "domains": {
                "text_accuracy": {"score": 8, "issue": "...", "suggestion": "..."},
                "anatomy": {"score": 7, ...},
                ...
            },
            "pass_checklist": true,
            "suggestions": ["Make the red darker for better contrast", ...]
        }
    """
    from src.quality_eval import evaluate_figure_quality
    
    return await evaluate_figure_quality(
        image_path=image_path,
        figure_type=figure_type,
    )


@mcp.tool()
async def batch_generate(
    pmids: list[str],
    figure_type: str = "auto",
    output_dir: Optional[str] = None,
) -> dict:
    """Generate medical figures for multiple papers at once.
    
    Useful for creating a batch of graphic abstracts from a literature review.
    
    Args:
        pmids: List of PubMed IDs
        figure_type: Figure type (applies to all, or auto per-paper)
        output_dir: Directory for output images (default: ./figures/)
    
    Returns:
        {
            "total": 5,
            "success": 4,
            "failed": 1,
            "figures": [
                {"pmid": "123", "image_path": "...", "status": "success"},
                {"pmid": "456", "error": "...", "status": "error"},
                ...
            ]
        }
    """
    from src.orchestrator import run_batch_pipeline
    
    return await run_batch_pipeline(
        pmids=pmids,
        figure_type=figure_type,
        output_dir=output_dir,
    )

# ──────────────────────────────────────────────────────────────
# MCP Server Entry Point
# ──────────────────────────────────────────────────────────────

def main():
    """Run the MCP server via stdio (for VS Code Copilot integration)."""
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
