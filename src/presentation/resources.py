"""MCP resource definitions — static discovery payloads."""

from __future__ import annotations

import json

from src.presentation.server import mcp


def _knowledge_assets() -> list[str]:
    return [
        "templates/prompt-templates.md",
        "templates/anatomy-color-standards.md",
        "templates/journal-figure-standards.md",
        "templates/gemini-tips.md",
        "templates/model-benchmark.md",
        "templates/code-rendering.md",
        "templates/scientific-figures-guide.md",
        "templates/ai-medical-illustration-evaluation.md",
    ]


@mcp.resource("academic-figures://inventory")
def inventory_resource() -> str:
    """Server inventory for MCP hosts and agent discovery."""
    return json.dumps(
        {
            "server": "academic-figures",
            "positioning": (
                "Multi-step academic figure agent harness for planning, "
                "generation, evaluation, and iteration."
            ),
            "sdk_baseline": "mcp[cli]>=1.27.0",
            "transports": ["stdio", "streamable-http"],
            "workflow_stages": [
                "ingest structured academic source",
                "reason about scientific concept and communication goal",
                "select figure type and rendering route",
                "assemble structured prompt and constraints",
                "generate figure output",
                "evaluate academic quality",
                "iterate toward publication-grade output",
            ],
            "supported_image_providers": {
                "google": {
                    "api_key_env": "GOOGLE_API_KEY",
                    "default_model": "gemini-3.1-flash-image-preview",
                },
                "openrouter": {
                    "api_key_env": "OPENROUTER_API_KEY",
                    "provider_env": "AFM_IMAGE_PROVIDER=openrouter",
                    "default_model": "google/gemini-3.1-flash-image-preview",
                },
                "ollama": {
                    "api_key_env": None,
                    "provider_env": "AFM_IMAGE_PROVIDER=ollama",
                    "default_model": "llava:latest",
                    "route": "local SVG brief generation + vision-based evaluation",
                },
            },
            "planned_render_routes": [
                "image_generation",
                "image_edit",
                "code_render_matplotlib",
                "code_render_d2",
                "code_render_mermaid",
                "code_render_svg",
                "layout_assemble_svg",
                "render_gateway_kroki",
                "vector_scene_edit",
            ],
            "tools": [
                "plan_figure",
                "generate_figure",
                "edit_figure",
                "evaluate_figure",
                "batch_generate",
            ],
            "resources": [
                "academic-figures://inventory",
                "academic-figures://gemini-image-baseline",
                "academic-figures://renderer-ecosystem",
            ],
            "prompts": [
                "plan_figure_request",
                "transform_figure_request",
            ],
            "knowledge_assets": _knowledge_assets(),
            "tracked_ecosystem": [
                "D2",
                "Mermaid",
                "Kroki",
                "Matplotlib",
                "SciencePlots",
                "FigureFirst",
                "CairoSVG",
                "Excalidraw",
                "tldraw",
            ],
        },
        indent=2,
        ensure_ascii=False,
    )


@mcp.resource("academic-figures://gemini-image-baseline")
def gemini_image_baseline_resource() -> str:
    """Official Gemini image-generation defaults used by this repo."""
    return json.dumps(
        {
            "default_model": "gemini-3.1-flash-image-preview",
            "high_fidelity_model": "gemini-3-pro-image-preview",
            "low_latency_model": "gemini-2.5-flash-image",
            "openrouter_compatible_model": "google/gemini-3.1-flash-image-preview",
            "provider_switch_env": "AFM_IMAGE_PROVIDER",
            "python_sdk": "from google import genai; from google.genai import types",
            "single_turn_api": "client.models.generate_content(...)",
            "multi_turn_api": "client.chats.create(...); chat.send_message(...)",
            "openrouter_api": "POST /api/v1/chat/completions with modalities=['image','text']",
            "response_parts": ["text", "inline_data"],
            "image_sizes": ["512", "1K", "2K", "4K"],
            "aspect_ratios": [
                "1:1",
                "1:4",
                "1:8",
                "2:3",
                "3:2",
                "3:4",
                "4:1",
                "4:3",
                "4:5",
                "5:4",
                "8:1",
                "9:16",
                "16:9",
                "21:9",
            ],
            "reference_image_limit": 14,
            "notes": [
                "Use multi-turn chats for iterative editing.",
                (
                    "OpenRouter image generation returns base64 data URLs under "
                    "choices[0].message.images."
                ),
                "Store grounding metadata when Google Search grounding is enabled.",
                "Prefer code/SVG for text-heavy or numerically exact figures.",
                "All generated images include SynthID watermarking.",
            ],
        },
        indent=2,
        ensure_ascii=False,
    )


@mcp.resource("academic-figures://renderer-ecosystem")
def renderer_ecosystem_resource() -> str:
    """Tracked open-source renderer and editor ecosystem."""
    return json.dumps(
        {
            "shortlist": [
                {
                    "name": "D2",
                    "role": "primary structured diagram DSL",
                    "integration": ["mcp", "vscode-extension", "backend-rendering"],
                },
                {
                    "name": "Mermaid",
                    "role": "lightweight flowchart and timeline DSL",
                    "integration": ["mcp", "vscode-extension", "backend-rendering"],
                },
                {
                    "name": "Kroki",
                    "role": "optional compatibility render gateway",
                    "integration": ["mcp", "backend-rendering"],
                },
                {
                    "name": "Matplotlib",
                    "role": "canonical chart engine",
                    "integration": ["mcp", "backend-rendering"],
                },
                {
                    "name": "SciencePlots",
                    "role": "publication-style preset source",
                    "integration": ["mcp", "backend-rendering"],
                },
                {
                    "name": "FigureFirst",
                    "role": "multi-panel SVG layout pattern",
                    "integration": ["backend-rendering"],
                },
                {
                    "name": "CairoSVG",
                    "role": "SVG export and derivative conversion",
                    "integration": ["backend-rendering"],
                },
                {
                    "name": "Excalidraw",
                    "role": "lightweight editable scene format",
                    "integration": ["vscode-extension"],
                },
                {
                    "name": "tldraw",
                    "role": "advanced interactive editor SDK",
                    "integration": ["vscode-extension"],
                },
            ],
            "capabilities": {
                "precise_layout": ["FigureFirst", "CairoSVG", "D2"],
                "code_generated_charts": ["Matplotlib", "SciencePlots"],
                "flowcharts": ["Mermaid", "D2", "Kroki"],
                "vector_editing": ["tldraw", "Excalidraw"],
                "asset_transformation": ["CairoSVG", "Kroki", "image_edit"],
                "vscode_embedding": ["D2", "Mermaid", "Excalidraw", "tldraw"],
            },
        },
        indent=2,
        ensure_ascii=False,
    )
