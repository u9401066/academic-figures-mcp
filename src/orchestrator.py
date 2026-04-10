"""
Core orchestrator — the LLM workflow engine.

This is where the magic happens:
- 7-block prompt assembly
- PubMed metadata fetching
- Gemini API calls
- Quality evaluation & intelligent retry
"""

import os
import json
import time
import re
from pathlib import Path
from typing import Optional

# These will be implemented with actual Google API calls
# For now: architecture sketch

GEN_API_KEY_ENV = "GOOGLE_API_KEY"
PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


async def fetch_pubmed(pmid: str) -> dict:
    """Fetch paper metadata from PubMed."""
    import httpx
    base = PUBMED_BASE
    url = f"{base}/esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        data = resp.json()
        result = data["result"][pmid]
        return {
            "pmid": pmid,
            "title": result.get("title", ""),
            "authors": result.get("fullauthorname", result.get("authors", "")),
            "journal": result.get("fulljournalname", ""),
            "pubdate": result.get("pubdate", ""),
            "abstract": await fetch_abstract(pmid),
        }


async def fetch_abstract(pmid: str) -> str:
    """Fetch the full abstract."""
    import httpx
    url = f"{PUBMED_BASE}/efetch.fcgi?db=pubmed&id={pmid}&rettype=abstract&retmode=text"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        text = resp.text
        # Parse abstract from XML/text
        return text[:2000]  # truncated for now


def classify_figure_type(paper_info: dict) -> str:
    """LLM-driven: decide the best figure type for the paper."""
    # Would call Gemini Pro / Sonnet for classification
    title = paper_info.get("title", "").lower()
    if "consensus" in title or "guideline" in title:
        return "flowchart"
    if "mechanism" in title or "pathway" in title:
        return "mechanism"
    if "randomized" in title or "comparison" in title:
        return "comparison"
    return "infographic"


def build_prompt_7block(paper_info: dict, figure_type: str, language: str = "zh-TW") -> str:
    """
    Build the 7-block prompt using reference templates.
    
    The 7 blocks:
    1. TITLE+PURPOSE — What the figure is about
    2. LAYOUT — Visual structure (grid, flow, hierarchy)
    3. ELEMENTS — What needs to be drawn (organs, arrows, labels)
    4. COLOR — Color scheme (journal-compliant)
    5. TEXT — Text content for labels, citations
    6. STYLE — Artistic style (hand-drawn, flat medical, etc.)
    7. SIZE — Canvas dimensions
    """
    # Load templates from references/
    template_dir = Path(__file__).parent.parent / "templates"
    templates_file = template_dir / "prompt_templates.md"
    
    # This would load the actual prompt templates and fill in the paper info
    # For now: architecture placeholder
    return f"[7-block prompt for: {paper_info['title']}, type={figure_type}]"


async def generate_image(prompt: str, image_size: str = "1024x1536") -> dict:
    """Call Google Gemini Image API to generate the figure."""
    import httpx
    
    api_key = os.environ.get(GEN_API_KEY_ENV)
    if not api_key:
        return {"status": "error", "error": "GOOGLE_API_KEY not set"}
    
    # Actual Gemini API call would go here
    # Using Gemini 3.1 Flash Image Preview
    model = "gemini-3.1-flash-image-preview"
    model_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
    
    # Placeholder
    return {
        "status": "pending_implementation",
        "note": "Full Gemini API integration goes here",
        "model": model,
    }


async def run_generate_pipeline(
    pmid: str,
    figure_type: str = "auto",
    language: str = "zh-TW",
    output_size: str = "1024x1536",
) -> dict:
    """Main pipeline for generating a medical figure."""
    start = time.time()
    
    try:
        # Step 1: Fetch paper metadata
        paper = await fetch_pubmed(pmid)
        
        # Step 2: Classify figure type (or use provided)
        if figure_type == "auto":
            figure_type = classify_figure_type(paper)
        
        # Step 3: Build 7-block prompt
        prompt = build_prompt_7block(paper, figure_type, language)
        
        # Step 4: Generate image
        result = await generate_image(prompt, output_size)
        
        # Step 5: Quality evaluation (LLM vision)
        # Would call Gemini Vision to score the output
        
        elapsed = time.time() - start
        
        return {
            "status": "success",
            "pmid": pmid,
            "figure_type": figure_type,
            "title": paper.get("title", "Unknown"),
            "image_path": result.get("image_path", ""),
            "quality_scores": result.get("quality_scores", {}),
            "elapsed_seconds": round(elapsed, 1),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "pmid": pmid,
        }


async def run_edit_pipeline(image_path: str, feedback: str, max_retries: int = 2) -> dict:
    """Refine a figure based on natural language feedback."""
    # Would use Gemini image editing API with the feedback translated
    # into proper edit instructions
    return {"status": "pending_implementation"}


async def run_batch_pipeline(pmids: list, figure_type: str = "auto", output_dir: Optional[str] = None) -> dict:
    """Generate figures for multiple papers."""
    figures = []
    success = 0
    for pmid in pmids:
        result = await run_generate_pipeline(pmid, figure_type)
        if result["status"] == "success":
            success += 1
        figures.append(result)
    return {
        "total": len(pmids),
        "success": success,
        "failed": len(pmids) - success,
        "figures": figures,
    }
