# Roadmap

This roadmap tracks the next product capabilities for Academic Figures MCP beyond the current generic renderer, planning flow, and YAML-backed journal registry.

## Current Baseline

- One public generation contract centered on generic planned_payload rendering.
- MCP planning, generation, editing, evaluation, and batch workflows.
- YAML-backed journal requirement injection for Nature, Science, JAMA, NEJM, and Lancet.
- Direct-run support through afm-run for plan, generate, transform, and evaluate flows.

## Roadmap Themes

### Theme 1: Reproducibility and Retargeting

Status: shipped (file-backed manifests, replay + retarget tooling are live)

Goals:

- Persist prompt packs and generation manifests so an output can be reproduced later.
- Retarget one existing image to a different journal profile without rebuilding the concept from zero.
- Keep journal conversion explainable by storing both the source prompt pack and the target journal constraints.

Planned deliverables:

- Saved job manifest per asset. ✅ Saved to `.academic-figures/manifests` with prompt, payload, provider, and journal metadata.
- Prompt and prompt-pack replay flow. ✅ `replay_manifest` + `list_manifests` MCP tools allow reruns from disk without rebuilding prompts.
- Image-to-journal retargeting workflow. ✅ `retarget_journal` injects a new profile and regenerates with a new manifest.
- Before and after journal constraint diff in metadata. ✅ Retarget responses include a diff between the previous and new journal profiles.

Mapped user requirements:

- Requirement 4: maintain one image while switching journal requirements.
- Requirement 5: retain prompt for future regeneration.

### Theme 2: Multi-Panel and Composite Figures

Status: in progress (composite render route shipped; planning schemas next)

Goals:

- Support grouped figure generation as a first-class planning target.
- Assemble multiple source images into one master figure with panel labels, spacing, and export rules.
- Handle common academic montage cases such as four images merged into a single large figure.

Planned deliverables:

- Multi-panel figure schema in planned_payload. ✅ `planned_payload.panels` accepted with `render_route=composite_figure` for assembly.
- Panel layout presets and panel-label rules. ⏳ Current assembler applies balanced columns with auto labels; presets remain planned.
- Composite assembly tool or route. ✅ `generate_figure` now supports a composite render route; `composite_figure` tool remains for direct calls.
- Single-output export for montage figures. ✅ Output is written as a single PNG with DPI metadata.

Mapped user requirements:

- Requirement 2: generate grouped figures.
- Requirement 3: generate stitched composite figures from multiple images.

### Theme 3: Poster Workflow

Status: planned

Goals:

- Treat posters as a separate output class rather than just a large infographic.
- Support section-aware layouts, title bands, methods/results zones, figure placement, and citation areas.
- Make poster generation journal-aware or conference-aware where needed.

Planned deliverables:

- Poster asset_kind and planning route.
- Poster layout presets.
- Large-canvas export rules.
- Text-density and readability guardrails.

Mapped user requirements:

- Requirement 1: generate posters.

### Theme 4: Style Intelligence and Reuse

Status: discovery

Goals:

- Infer reusable style prompts from an existing image.
- Separate content semantics from reusable style semantics so the extracted style can be applied again.
- Turn image-derived style into a stored preset that can be reused across future jobs.

Planned deliverables:

- Style extraction workflow from an existing image.
- Reusable style prompt or style profile artifact.
- Style replay against new planned_payload jobs.

Mapped user requirements:

- Requirement 6: convert image elements into a reusable style prompt.

## Sequencing

1. Prompt persistence and replay. ✅
2. Journal retargeting for existing assets. ✅
3. Grouped figure planning and composite assembly. ▶️ composite route shipped; grouped planning next.
4. Layer-aware image decomposition (vision-model, Phase 1). ⏳ spec complete.
5. Poster-specific planning and export.
6. Precision segmentation and editable export (Phase 2).
7. Image-to-style extraction and reuse.
8. Native layered generation (Phase 3).

### Theme 5: Layer-Aware Image Decomposition

Status: planned (spec complete, implementation not started)

Goals:

- Transform flat generated figures into editable scene graphs of individually adjustable layer objects.
- Enable per-layer editing (move, resize, restyle, replace, remove) without regenerating the entire figure.
- Export decomposed scenes to editable formats (SVG, PSD) for handoff to professional editors.
- Evolve toward native layered generation that produces pre-decomposed scene graphs without post-hoc segmentation.

Planned deliverables:

- Vision-model layer decomposition using Gemini (Phase 1). ⏳ Spec complete in `docs/spec-layer-decomposition.md`.
- Precision segmentation with SAM2/GroundingDINO for pixel-perfect masks (Phase 2).
- Native layered generation pipeline producing per-element images on transparent backgrounds (Phase 3).
- MCP tools: `decompose_figure`, `edit_layer`, `recompose_scene`, `list_scenes`, `export_scene`.
- FigureScene aggregate root in domain layer with Layer entities, BoundingBox and LayerStyle value objects.

Mapped user requirements:

- Core differentiator vs. Google NotebookLM and other multi-step generators.
- Requirement for precise, non-destructive editing of generated academic figures.
- Requirement for editable export to professional tools (Inkscape, Illustrator, Figma).

Full specification: [`docs/spec-layer-decomposition.md`](docs/spec-layer-decomposition.md)
Strategic roadmap: [`docs/roadmap-v2.md`](docs/roadmap-v2.md)

## Out of Scope for This Roadmap

- Building a full academic literature search platform inside this repository.
- Replacing the single public renderer with multiple competing public creation APIs.
- Treating provider-specific prompt tricks as the source of truth instead of structured job metadata.
