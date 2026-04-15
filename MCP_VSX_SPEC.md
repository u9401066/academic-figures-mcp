# Academic Figures MCP + VSX Spec

Status: working draft
Date: 2026-04-11
Scope: MCP server for agent-first academic figure generation, plus VS Code extension for Copilot agent and human-in-the-loop workflows.
Baseline targets: MCP Python SDK 1.27.0 and Google Gemini image-generation docs updated 2026-03-31.

## 1. Product Goal

Turn this repo from a prompt/template collection with a thin MCP wrapper into a complete academic-figure system with two deliverables:

1. An MCP server that agents can call to plan, generate, transform, evaluate, and iterate scientific figures.
2. A VS Code extension that exposes the same workflow to Copilot and human users through commands, views, presets, and asset management.

The system must support both first-pass figure generation and iterative refinement, including style conversion with default domain presets.

## 2. Target Users

1. Copilot agent workflows that need tool-level access to figure planning and generation.
2. OpenClaw or other multi-step agents that need structured figure planning, retries, and evaluation.
3. Researchers who start from a PMID and want a journal-style figure draft.
4. Users who start from an existing image and want style transfer, relabeling, or journal adaptation.

## 3. Core User Stories

1. As an agent, I can give a PMID and receive a figure plan, prompt pack, suggested figure type, and generation result.
2. As an agent, I can ask for a style conversion such as Netter-like schematic, Nature multi-panel, or journal-safe infographic, with defaults filled from built-in references.
3. As a user, I can inspect available presets, template sources, evaluation rubrics, and rendering routes before generation.
4. As a user, I can refine a generated figure over multiple turns while preserving citation, label language, and layout intent.
5. As a user, I can evaluate a figure against scientific, visual, and publication criteria.
6. As a host, I can inspect a manifest's full review timeline and write back an external visual-review verdict.

## 4. Product Boundary

In scope:

1. PubMed metadata retrieval and figure planning.
2. Prompt-based image generation via Gemini.
3. Style preset injection for generation and transformation.
4. Code-based figure routes for charts, flowcharts, and precise layouts when image generation is weak.
5. Figure evaluation and retry guidance.
6. VS Code extension UX for commands, preset browsing, preview, asset history, and MCP bootstrap.

Out of scope for MVP:

1. Cloud-hosted asset storage.
2. Multi-user collaboration.
3. Full journal submission packaging.
4. Fine-tuned custom models.

## 5. Current Repo Inventory

### 5.1 Runtime and Packaging

1. pyproject.toml defines a Python package named academic-figures-mcp with script entry points afm-server and afm-run.
2. The runtime is already aligned on mcp[cli]>=1.27.0 with httpx, google-genai, and pillow.
3. Python target is 3.10+.
4. This repository is greenfield. There is no backward-compatibility requirement for older package names, shim modules, or legacy entrypoints.

### 5.2 Existing Python Modules

1. src/presentation/server.py
   Role: canonical FastMCP server entry point.
   Current tools and surfaces: tools, prompts, and resources are all registered here.
   Current state: runtime entrypoint for MCP hosts via afm-server.

2. src/presentation/direct_run.py
   Role: canonical direct-run CLI for VS Code and local automation.
   Current commands: plan, generate, evaluate, transform, batch.
   Current state: JSON-oriented command surface for extension workflows via afm-run.

3. src/presentation/tools.py
   Role: MCP tool handlers for planning, generation, editing, verification, manifest inspection, host-review write-back, and replay surfaces.
   Current strength: validates inputs at the presentation boundary before resolving dependencies.

4. src/application/*
   Role: use-case orchestration for planning, generation, editing, evaluation, and batch execution.
   Current strength: request objects and use cases are separated from infrastructure.

5. src/domain/*
   Role: figure classification, entities, exceptions, interfaces, and value objects.
   Current strength: domain remains independent from external packages.

6. src/infrastructure/*
   Role: provider config, multi-provider generation adapter, prompt engine, and PubMed metadata fetcher.
   Current strength: concrete integrations are isolated behind domain interfaces.

### 5.3 Current Review and Manifest Contract

1. Provider-side review is first-class runtime behavior: `generate_figure`, `replay_manifest`, and `retarget_journal` can run automated Google/OpenRouter vision review and persist the verdict into each manifest.
2. Host-side review is an external-but-tracked route: Copilot or another host model inspects the image outside MCP execution and writes the verdict back through `record_host_review`.
3. `list_manifests` is intentionally a summary surface; `get_manifest_detail` is the load-by-id tool for full manifest payloads, lineage context, and flattened review history.
4. The persisted review policy is currently `provider_vision_required_host_optional`: `provider_vision` is the baseline gate and must pass, while `host_vision` remains optional and supplemental.

### 5.4 Knowledge Base Templates

1. templates/prompt-templates.md
   Contains multi-format prompt templates, including clinical flowchart, drug mechanism, comparison, anatomy, architecture, Nature-style multi-panel, and journal-ready patterns.

2. templates/anatomy-color-standards.md
   Contains anatomy color mappings and rationale for arteries, veins, nerves, muscles, bone, fascia, cartilage, skin, and other structures.

3. templates/journal-figure-standards.md
   Contains Nature and Lancet size, font, DPI, panel-label, and palette constraints.

4. templates/gemini-tips.md
   Contains Gemini image generation best practices, model guidance, and multi-turn editing notes.

5. templates/model-benchmark.md
   Contains model comparison notes between Gemini and other image models.

6. templates/code-rendering.md
   Contains non-image-generation figure routes such as matplotlib, SVG, Mermaid, TikZ, and PlantUML.

7. templates/scientific-figures-guide.md
   Contains route-selection guidance for statistical plots, flowcharts, architecture diagrams, and other figure classes.

8. templates/ai-medical-illustration-evaluation.md
   Contains the evaluation rubric, common failure modes, and quality thresholds.

### 5.5 Agent and Workspace Assets

1. .github/*.chatmode.md provides architect, ask, code, and debug chat modes for Copilot workflows.
2. memory-bank/* is actively used to record current architecture, decisions, and progress.
3. README.md explains the MCP server, direct-run flow, providers, competitive landscape, and VS Code extension at a high level.

### 5.6 Current Risks and Gaps

1. Plaintext local env files remain a commit-risk and should stay optional rather than becoming the default runtime path.
2. Style conversion still depends more on prompt/template knowledge than on a fully structured preset registry.
3. Plan-first orchestration is still a soft convention; the server does not yet enforce workflow state such as `plan_id` or stage transitions.
4. PubMed retrieval is intentionally thin; richer discovery should be integrated from an external research-search MCP rather than reimplemented here.
5. Deterministic render routes are recommended by the planner, but most of those routes are not yet implemented as first-class execution backends.

## 6. Target Architecture

### 6.1 Logical Components

1. Metadata layer
   Responsibilities: PubMed fetch, local caching, paper normalization.

2. Planning layer
   Responsibilities: figure classification, route selection, style preset resolution, prompt pack assembly.

3. Rendering layer
   Responsibilities: Gemini generation, Gemini image edit, code-based rendering, export normalization.

4. Evaluation layer
   Responsibilities: rubric-based critique, retry suggestions, route-switch suggestions.

5. Preset registry
   Responsibilities: structured access to style packs, journal packs, anatomy color packs, and rendering defaults.

6. Asset/job layer
   Responsibilities: job ids, prompt history, outputs, evaluation reports, source references.

7. MCP interface layer
   Responsibilities: stable tool schemas for agents.

8. VSX extension layer
   Responsibilities: command palette, tree views, webview preview, asset explorer, server bootstrap, secret configuration.

### 6.2 Proposed Package Structure

The current src layout is already centered on this DDD-oriented structure and should continue evolving without adding legacy wrapper modules:

```text
src/
   domain/
      classifier.py
      entities.py
      exceptions.py
      interfaces.py
      value_objects.py
   application/
      batch_generate.py
      edit_figure.py
      evaluate_figure.py
      generate_figure.py
      plan_figure.py
   infrastructure/
      config.py
      gemini_adapter.py
      prompt_engine.py
      pubmed_client.py
   presentation/
      dependencies.py
      direct_run.py
      prompts.py
      resources.py
      server.py
      tools.py
      validation.py
```

This structure is the product baseline. New work should extend these layers directly rather than preserving obsolete import paths.

## 7. Style Preset System

This is the most important missing feature for image style conversion.

### 7.1 Preset Types

1. Journal preset
   Examples: Nature multi-panel, Lancet clinical figure, generic review infographic.

2. Visual style preset
   Examples: Netter-like anatomy, flat medical infographic, clean white paper schematic, high-contrast presentation slide, publication-safe statistical chart.

3. Domain preset
   Examples: drug mechanism, airway anatomy, clinical workflow, trial comparison, PK/PD chart.

4. Language preset
   Examples: zh-TW labels, bilingual labels, English-only journal mode.

5. Output preset
   Examples: portrait poster, double-column journal, slide-ready wide canvas.

### 7.2 Preset Fields

Each preset should expose a structured object:

```json
{
  "id": "nature_multi_panel",
  "label": "Nature Multi-Panel",
  "category": "journal",
  "description": "Publication-style multi-panel scientific figure",
  "default_canvas": "183mm x 247mm equivalent",
  "layout_rules": ["lowercase panel labels", "minimal whitespace"],
  "color_rules": ["Wong-safe palette", "no red-green conflicts"],
  "text_rules": ["Arial or Helvetica", "5-7pt body text"],
  "render_route": "image_generation",
  "source_files": [
    "templates/journal-figure-standards.md",
    "templates/prompt-templates.md"
  ]
}
```

### 7.3 Preset Resolution Rules

1. User-explicit preset always wins.
2. If no explicit preset is provided, the planner resolves journal preset from requested target.
3. Domain preset is inferred from paper classification or user instruction.
4. Rendering route is then selected from preset plus figure type.
5. Final prompt pack includes both human-readable and machine-structured preset data.

## 8. Rendering Route Selection

The planner must choose among routes rather than forcing all output through image generation.

### 8.1 Routes

1. image_generation
   Best for anatomy, mechanism diagrams, medical illustrations, conceptual infographics.

2. image_edit
   Best for iterative refinement of an existing image.

3. code_render_matplotlib
   Best for forest plots, ROC curves, Kaplan-Meier curves, dose-response, and other quantitative charts.

4. code_render_d2
   Best for structured mechanism diagrams, architecture diagrams, and publication-minded flow diagrams with stronger theming control.

5. code_render_mermaid
   Best for small flowcharts, timelines, and protocol diagrams when speed and readability matter more than exact layout.

6. code_render_svg
   Best for exact layout, label control, and style-constrained diagrams.

7. layout_assemble_svg
   Best for precise multi-panel figure assembly, mixed chart-plus-annotation layouts, and journal-style panel alignment.

8. render_gateway_kroki
   Best for compatibility rendering across D2, Mermaid, PlantUML, and other text-to-diagram engines behind a single API.

9. vector_scene_edit
   Best for human-in-the-loop cleanup, annotation, and manual panel refinement through an editable scene model.

### 8.2 Route Heuristics

1. Statistical or numeric figure requests default to `code_render_matplotlib`, with `SciencePlots`-backed style presets layered on top.
2. Complex anatomy defaults to `image_generation` with a schematic simplification note and post-generation evaluation.
3. Small clinical workflows and quick protocol diagrams prefer `code_render_mermaid`.
4. Structured mechanism, architecture, and publication-style concept diagrams prefer `code_render_d2`.
5. Requests emphasizing precise text layout, bilingual labeling, or exact journal panel placement prefer `code_render_svg` or `layout_assemble_svg`.
6. Multi-panel review figures that mix deterministic charts and annotations should assemble through `layout_assemble_svg`, using a FigureFirst-like pipeline.
7. Compatibility fallback across heterogeneous diagram DSLs should use `render_gateway_kroki`, preferably self-hosted.
8. Style conversion from an existing raster image defaults to `image_edit` unless the request is really a redraw into a structured diagram route.
9. If the user needs manual cleanup or extension-side editing, switch the asset into `vector_scene_edit` using an Excalidraw-like or tldraw-like scene model.

### 8.3 External Repository Shortlist

The following open-source repositories are the most relevant references to track and selectively borrow from:

| Repo | Category | Relevant strengths | Recommended role in this product |
| ---- | -------- | ------------------ | -------------------------------- |
| `D2` | Text-to-diagram DSL | Themes, multiple layout engines, LaTeX, strong VS Code fit | Primary structured diagram DSL for publication-minded workflows |
| `Mermaid` | Text-to-diagram DSL | Fast SVG output, huge ecosystem, simple syntax | Lightweight flowchart and timeline DSL |
| `Kroki` | Render gateway | One API for multiple diagram engines | Optional self-hosted compatibility gateway |
| `Matplotlib` | Scientific chart engine | Deterministic, publication-grade charts, broad export support | Canonical chart renderer |
| `SciencePlots` | Chart style layer | Nature/science-like presets, colorblind-aware palettes | Style preset source over Matplotlib |
| `FigureFirst` | SVG layout-first assembly | Multi-panel figure composition from SVG templates and charts | Precise panel assembly pattern |
| `CairoSVG` | SVG conversion/export | Reliable SVG to PNG/PDF/EPS conversion in Python | Export stage for preview and journal outputs |
| `Excalidraw` | Editable vector scene | Scene JSON, SVG export, embeddable editor | Lightweight editable scene format for future extension UX |
| `tldraw` | Editable vector scene | Custom shapes/tools, rich editor SDK | Advanced interactive editor and scientific custom shape layer |

`PlantUML` and `diagrams.net` remain useful compatibility references, but they should stay secondary rather than define the core product model.

### 8.4 Capability Matrix

| Capability | Primary choice | Secondary choice | Product implication |
| ---------- | -------------- | ---------------- | ------------------- |
| Precise layout | `layout_assemble_svg` with FigureFirst-like templates | direct SVG authoring | Use a layout-first path for mixed panel figures |
| Code-generated charts | `Matplotlib` + `SciencePlots` | `seaborn` as authoring helper | Separate chart engine from chart style presets |
| Flowcharts | `Mermaid` for light cases, `D2` for publication cases | `Kroki` as compatibility layer | Do not force all diagrams through one DSL |
| Vector editing | `tldraw` for rich custom tools | `Excalidraw` for lightweight scenes | Define an editable scene asset model early |
| Asset transformation | `CairoSVG`, `layout_assemble_svg`, `image_edit` | `Kroki` for DSL conversions | Export and transformation are their own layer |
| VS Code embedding | `D2`, `Mermaid`, `Excalidraw`, `tldraw` | `diagrams.net` later | MVP should stay text-first with live preview |

### 8.5 Product Implications from Repo Research

1. This product should be explicitly positioned as a multi-route academic figure system, not only a Gemini prompt wrapper.
2. `D2` should become a first-class route next to `Mermaid`, because it better fits themed, publication-oriented structured diagrams.
3. `Matplotlib` and `SciencePlots` should be modeled separately as engine plus style layer rather than one blended route.
4. `FigureFirst` and `CairoSVG` justify a dedicated `layout_assemble_svg` pipeline for journal-ready multi-panel outputs.
5. `Kroki` is valuable as an optional self-hosted gateway, not as the single rendering backbone.
6. Editable vector scenes should be a future asset type so the extension can support manual cleanup without leaving the workspace.
7. `PlantUML` and `diagrams.net` should stay in the compatibility layer, not the product core.

## 9. MCP SDK 1.27 Surface

### 9.1 Server Primitives

1. Tools
   Execute generation, editing, evaluation, inspection, and batch operations.

2. Resources
   Expose static or semi-static knowledge such as preset indexes, supported models, journal packs, and render-route guidance.

3. Prompts
   Expose reusable interaction patterns for figure planning, style transfer, and evaluation requests.

4. Transports
   Default to stdio for Copilot and embedded agents, but keep streamable-http as a first-class debug and extension-development transport.

### 9.2 Core Tool Surface

1. generate_figure
   Input: `planned_payload` or direct source inputs such as `pmid` / `source_title`, plus optional `output_dir?`, `output_format?`.
   Output: asset path, asset kind, selected figure type, render route, model metadata, elapsed time, and plan linkage.

   This is the primary public bitmap-creation entrypoint. It should accept direct source inputs and perform planning internally when the host does not need an explicit planning step.
   When `output_format` is provided, the MCP layer should perform raster conversion internally instead of forcing the host to post-process provider output.

2. plan_figure
   Input: `pmid` or `source_title`, plus optional `source_kind?`, `source_summary?`, `source_identifier?`, `output_format?`, `figure_type?`, `style_preset?`, `language?`, `output_size?`.
   Output: figure classification, route recommendation, academic constraints, prompt preview, and a reusable `planned_payload` for `generate_figure`.

   This planning boundary must support PMID-backed papers, preprints, repositories, and freeform academic briefs without forcing everything through PubMed metadata lookup.

3. edit_figure
   Input: `image_path`, `feedback`, `output_path?`, `output_format?`.
   Output: edited asset path, model metadata, and elapsed time.

   This is a refinement harness around an existing asset, not a competing new-asset creation API.

4. evaluate_figure
   Input: `image_path`, `figure_type?`, `reference_pmid?`.
   Output: 8-domain evaluation text, blocking issues, model metadata, and elapsed time.

5. batch_generate
   Input: `pmids` or preplanned payloads, `figure_type?`, `language?`, `output_size?`, `output_dir?`.
   Output: orchestration results that repeatedly call the same `generate_figure` contract instead of introducing a second renderer.

### 9.3 Harness and Secondary Tools

1. continue_workflow
2. transform_figure_style
3. list_presets
4. inspect_resources
5. render_code_figure
6. explain_figure_choice
7. get_job_status
8. list_recent_assets

### 9.4 Example Generic Render Request Shape

```json
{
   "asset_kind": "academic_figure",
   "goal": "Create a publication-ready clinical flowchart from the provided plan.",
   "selected_figure_type": "flowchart",
   "render_route": "image_generation",
  "style_preset": "nature_multi_panel",
  "language": "zh-TW",
  "output_size": "1536x1024",
   "target_journal": "Nature",
   "source_context": {
      "pmid": "41657234"
   },
   "prompt_pack": {
      "prompt": "...",
      "negative_constraints": [],
      "source_files": []
   },
  "must_include": ["PMID footer", "clinical algorithm arrows"],
  "references": []
}
```

## 10. Gemini Image API Baseline

This project should align with the Google image-generation documentation updated on 2026-03-31.

### 10.1 SDK and Call Pattern

1. Use the official Google Gen AI SDK import path: from google import genai and from google.genai import types.
2. Single-turn generation should use client.models.generate_content(...).
3. Multi-turn editing should use client.chats.create(...) and chat.send_message(...).
4. Response parsing should iterate response.parts and handle both text parts and image parts via part.as_image().

### 10.2 Model Selection Policy

1. Default model for generation and iterative edits: gemini-3.1-flash-image-preview.
2. High-fidelity assets and harder text rendering: gemini-3-pro-image-preview.
3. Low-latency or bulk-friendly generation: gemini-2.5-flash-image.
4. Optional future branch: Imagen 4 or Imagen 4 Ultra for dedicated image-only workflows.

### 10.3 Config Surface

1. response_modalities should be explicitly set to TEXT plus IMAGE, or IMAGE only for asset-only calls.
2. image_config should expose aspect_ratio and image_size.
3. Supported 3.1 Flash Image sizes relevant to this repo are 512, 1K, 2K, and 4K.
4. Supported aspect ratios include 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9, plus the new 1:4, 4:1, 1:8, and 8:1 options.
5. For Gemini 3.1 Flash Image, the implementation should leave room for thinking-level control when the quality versus latency tradeoff matters.

### 10.4 Editing, References, and Grounding

1. Image editing is text plus image to image, using a prompt together with one or more input images.
2. Multi-turn editing should be the default refinement path because the SDK automatically handles thought signatures when chat history is preserved.
3. Gemini 3 image models can mix up to 14 reference images in a single workflow.
4. Google Search grounding and image search grounding should be optional planner features for fact-sensitive or reference-sensitive requests.
5. When grounding is used, grounding metadata should be stored with the job and surfaced in the extension UI.

### 10.5 Official Limits That Matter for This Product

1. Text-heavy diagrams still need a code or SVG fallback even though Gemini has stronger text rendering than older image models.
2. Transparent background generation is not supported.
3. The model may not return exactly the number of images requested, so the asset layer must not assume fixed counts.
4. The docs list English and zh-CN among best-supported languages, so zh-TW labeling should be validated post-generation.
5. All generated images include SynthID watermarking.
6. High-throughput generation should move to Batch API rather than synchronous loops.

## 11. VS Code Extension Spec

### 11.1 Purpose

Provide a first-class VS Code UI for running the MCP workflow, managing presets, previewing outputs, and making the system easy to use from Copilot agent and manual commands.

### 11.2 Extension Capabilities

1. Start and monitor the local MCP server.
2. Configure connection sources through VS Code SecretStorage, env file, or process environment.
3. Provide direct-run commands for planning, generation, transformation, evaluation, and asset reopening.
4. Show preset browser and resource browser in a side panel.
5. Persist generated artifacts under a workspace-local `.academic-figures/` directory.
6. Provide a setup wizard, status panel, and output channel for local workflow bootstrap.

### 11.3 Proposed Commands

1. Academic Figures: Plan Figure from PMID
2. Academic Figures: Generate Figure
3. Academic Figures: Transform Figure Style
4. Academic Figures: Evaluate Figure
5. Academic Figures: Browse Presets
6. Academic Figures: Browse Knowledge Assets
7. Academic Figures: Configure Connection
8. Academic Figures: Create Environment File
9. Academic Figures: Insert MCP Settings
10. Academic Figures: Open Recent Jobs
11. Academic Figures: Show Status
12. Academic Figures: Show Output
13. Academic Figures: Setup Wizard
14. Academic Figures: Reinstall Python Environment

### 11.4 Proposed Views

1. Presets view
   Sections: journal presets, visual style presets, domain presets, rendering routes.

2. Resources view
   Sections: prompt templates, color standards, journal standards, rendering guides, evaluation rubrics.

3. Jobs view
   Sections: recent plans, generated figures, failed jobs, evaluations.

### 11.5 Extension Output Artifacts

The extension should save workspace-local artifacts under a dedicated folder:

```text
.academic-figures/
  jobs/
  outputs/
  prompts/
  evaluations/
```

### 11.6 Secret Handling

1. Primary path: VS Code SecretStorage.
2. Secondary path: configured env file injection when launching the MCP server.
3. Third path: process environment for local shells and external launchers.
4. If a plaintext env file is detected, warn the user that it is not safe for commit.

## 12. Data Models

### 12.1 FigurePlan

```json
{
  "plan_id": "plan_20260410_001",
  "source": {
    "pmid": "41657234",
    "title": "...",
    "journal": "..."
  },
  "figure_type": "flowchart",
  "render_route": "image_generation",
  "resolved_presets": ["nature_multi_panel", "clinical_guideline_flowchart", "zh_tw_labels"],
   "planned_payload": {
      "asset_kind": "academic_figure",
      "selected_figure_type": "flowchart",
      "render_route": "image_generation",
      "style_preset": "nature_multi_panel",
      "language": "zh-TW",
      "output_size": "1536x1024",
      "references": [],
      "must_include": ["PMID footer"]
   },
  "prompt_pack": {
    "system_notes": [],
    "prompt": "...",
    "negative_constraints": [],
    "source_files": []
  },
  "risks": ["complex labels may garble in image model"]
}
```

### 12.2 FigureAsset

```json
{
  "asset_id": "asset_20260410_001",
  "plan_id": "plan_20260410_001",
  "path": ".academic-figures/outputs/asset_20260410_001.png",
  "kind": "generated_image",
  "created_at": "2026-04-10T12:00:00Z",
  "citations": ["PMID 41657234"],
  "applied_presets": ["nature_multi_panel"]
}
```

### 12.3 EvaluationReport

```json
{
  "asset_id": "asset_20260410_001",
  "total_score": 31,
  "domain_scores": {
    "accuracy": 4,
    "location": 4,
    "size_scale": 4,
    "color": 5,
    "complexity": 3,
    "educational_value": 4,
    "relevance": 4,
    "aesthetics": 3
  },
  "blocking_issues": [],
  "suggested_retry": false
}
```

## 13. Non-Functional Requirements

1. Reproducibility
   Persist prompt pack, resolved presets, and model metadata for every output.

2. Safety
   Never commit API keys or embed secrets in generated artifact metadata.

3. Explainability
   Every plan should expose why a figure type and render route were chosen.

4. Extensibility
   New presets and journals should be data additions, not code rewrites.

5. Workspace portability
   MCP server and extension should work locally on Windows first, then stay portable to macOS and Linux.

## 14. Implementation Phases

Phases 0 and 3 are already partially landed in the current repository. The list below is now best read as remaining work inside each phase, not as untouched future scope.

### Phase 0: Hardening

1. Add root secret ignore rules.
2. Keep config centered on environment variables while treating env files as an optional injection path.
3. Normalize data models and error shapes.

### Phase 1: Structured Knowledge Layer

1. Convert markdown-derived knowledge into structured preset registry.
2. Implement inspect_resources and list_presets.
3. Refactor prompt engine to consume structured preset objects.

### Phase 2: Real MCP Execution

1. Implement real Gemini generation and edit adapters using the official google.genai single-turn and chat-based image flows.
2. Persist plans, prompts, outputs, and evaluation reports.
3. Implement route selection, search-grounded generation options, and code-render fallback.

### Phase 3: VS Code Extension

1. Expand the existing extension package rather than scaffolding a new one.
2. Continue refining commands, tree views, and connection-mode UX.
3. Improve MCP bootstrap and artifact preview flows.

### Phase 4: Quality

1. Add test coverage for classification, preset resolution, prompt generation, and request validation.
2. Add end-to-end smoke tests for PMID to plan and image-to-style-transform workflows.

## 15. Definition of Done for MVP

1. A user can generate a figure plan from a PMID.
2. A user can generate at least one real image through the single generic render tool from the plan.
3. A user can transform an existing image using a named style preset.
4. A user can inspect built-in resource packs and presets.
5. A user can evaluate a figure and receive structured feedback.
6. A VS Code extension can launch the workflow and store the API key securely.

## 16. Immediate Backlog Derived from This Spec

1. Collapse the current PMID-bound public generation contract into one generic render request consumed by `generate_figure`.
2. Introduce a structured preset registry extracted from current template markdown files.
3. Enforce a plan-first workflow with server-side state such as `plan_id`, stage transitions, and reusable prompt packs.
4. Add first-class MCP tools for `transform_figure_style`, `list_presets`, and `inspect_resources` instead of relying only on prompts, resources, or extension-side commands.
5. Persist plans, prompts, outputs, and evaluations as typed job artifacts rather than only ad-hoc JSON payloads.
6. Implement deterministic rendering backends behind the planner's non-image routes, especially matplotlib, Mermaid, D2, and SVG assembly.
7. Strengthen artifact hygiene and repo validation automation so generated packaging output and stale config do not create editor noise.
