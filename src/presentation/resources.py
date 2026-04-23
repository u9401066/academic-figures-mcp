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
                "run provider-side automated review",
                "optionally record host-side visual review",
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
                "openai": {
                    "api_key_env": "OPENAI_API_KEY",
                    "provider_env": "AFM_IMAGE_PROVIDER=openai",
                    "default_model": "gpt-image-2",
                    "vision_review_model_env": "OPENAI_VISION_MODEL",
                    "route": "OpenAI Images API generation/editing + Responses API vision review",
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
                "prepare_publication_image",
                "evaluate_figure",
                "batch_generate",
                "composite_figure",
                "get_manifest_detail",
                "list_manifests",
                "replay_manifest",
                "record_host_review",
                "retarget_journal",
                "verify_figure",
                "multi_turn_edit",
            ],
            "review_contract": {
                "policy": "provider_vision_required_host_optional",
                "baseline_route": "provider_vision",
                "provider_required": True,
                "host_optional": True,
                "accepted_review_routes": ["provider_vision", "host_vision"],
                "provider_route_tool": "verify_figure",
                "host_write_back_tool": "record_host_review",
                "manifest_detail_tool": "get_manifest_detail",
                "extension_type_mapping_guidance": (
                    "If the VS Code extension starts consuming manifest/detail payloads "
                    "directly, map these typed review fields 1:1 into TypeScript "
                    "interfaces instead of reading raw nested dict keys ad hoc."
                ),
                "typed_fields": {
                    "quality_gate": [
                        "route",
                        "route_status",
                        "review_route",
                        "review_status",
                        "passed",
                    ],
                    "review_summary_route": [
                        "route",
                        "route_status",
                        "review_status",
                        "available",
                        "executed",
                        "passed",
                    ],
                    "manifest_list_item": [
                        "quality_gate.route_status",
                        "review_summary.routes.provider_vision.route_status",
                        "review_history_count",
                    ],
                    "manifest_detail": [
                        "manifest.quality_gate.route_status",
                        "manifest.review_history[].review_status",
                        "review_timeline[].route_status",
                    ],
                },
            },
            "error_contract": {
                "typed_fields": ["error_status", "error_category", "error"],
                "categories": [
                    "validation",
                    "configuration",
                    "domain",
                    "unsupported",
                    "contract",
                    "execution",
                    "generation_result",
                    "unknown",
                ],
                "extension_type_mapping_guidance": (
                    "When the VS Code extension starts reading manifest/detail or other "
                    "host-facing MCP payloads directly, map error_status/error_category "
                    "into TypeScript interfaces at the same time as the typed review schema."
                ),
            },
            "aggregate_contract": {
                "typed_fields": {
                    "core": ["aggregate_kind", "aggregate_status", "item_count"],
                    "batch_generate": ["total_count", "success_count", "failed_count"],
                    "list_manifests": ["item_count"],
                },
                "kinds": ["batch_generate", "list_manifests"],
                "statuses": [
                    "complete_success",
                    "complete_partial_failure",
                    "complete_failure",
                    "list_ready",
                ],
                "extension_type_mapping_guidance": (
                    "Do not add unused TypeScript runtime interfaces yet. When the VS Code "
                    "extension becomes a direct consumer of manifest/detail or aggregate MCP "
                    "payloads, map the stabilized review/error/aggregate typed fields into "
                    "TypeScript interfaces in the same slice."
                ),
            },
            "resources": [
                "academic-figures://inventory",
                "academic-figures://gemini-image-baseline",
                "academic-figures://provider-capabilities",
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


@mcp.resource("academic-figures://provider-capabilities")
def provider_capabilities_resource() -> str:
    """Provider capability matrix for MCP hosts and extension discovery."""
    return json.dumps(
        {
            "schema_version": "1.0",
            "provider_env": "AFM_IMAGE_PROVIDER",
            "providers": {
                "google": {
                    "generate": True,
                    "edit": True,
                    "verify": True,
                    "multi_turn_edit": True,
                    "mask_edit": False,
                    "structured_options": {
                        "aspect_ratio": True,
                        "output_size": False,
                        "quality": False,
                        "background": False,
                        "output_format": "postprocess",
                    },
                    "default_model": "gemini-3.1-flash-image-preview",
                },
                "openrouter": {
                    "generate": True,
                    "edit": True,
                    "verify": True,
                    "multi_turn_edit": False,
                    "mask_edit": False,
                    "structured_options": {
                        "aspect_ratio": True,
                        "output_size": False,
                        "quality": False,
                        "background": False,
                        "output_format": "postprocess",
                    },
                    "default_model": "google/gemini-3.1-flash-image-preview",
                },
                "openai": {
                    "generate": True,
                    "edit": True,
                    "verify": True,
                    "multi_turn_edit": False,
                    "mask_edit": "api_supported_not_exposed_as_mcp_argument",
                    "structured_options": {
                        "aspect_ratio": False,
                        "output_size": True,
                        "quality": "OPENAI_IMAGE_QUALITY",
                        "background": "OPENAI_IMAGE_BACKGROUND",
                        "output_format": "OPENAI_IMAGE_OUTPUT_FORMAT",
                    },
                    "default_model": "gpt-image-2",
                    "image_model_env": "OPENAI_IMAGE_MODEL",
                    "vision_model_env": "OPENAI_VISION_MODEL",
                    "api_key_env": "OPENAI_API_KEY",
                    "endpoints": [
                        "POST /v1/images/generations",
                        "POST /v1/images/edits",
                        "POST /v1/responses",
                    ],
                },
                "ollama": {
                    "generate": "local_svg_brief",
                    "edit": False,
                    "verify": True,
                    "multi_turn_edit": False,
                    "mask_edit": False,
                    "structured_options": {
                        "aspect_ratio": "prompt_to_svg_canvas",
                        "output_size": "prompt_to_svg_canvas",
                        "quality": False,
                        "background": False,
                        "output_format": "svg_or_postprocess",
                    },
                    "default_model": "llava:latest",
                },
            },
            "planned_payload_contract": {
                "schema_version": "planned_payload_v1",
                "required_for_generate": ["render_route", "title_or_asset_kind"],
                "provider_forwarded_fields": ["output_size", "output_format", "model"],
                "notes": [
                    "output_size is forwarded as a structured provider hint when supported.",
                    (
                        "output_format still uses post-generation conversion except for "
                        "OpenAI image output."
                    ),
                ],
            },
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
