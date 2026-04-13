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

Status: shipped (composite render route + layout presets + panel-label rules)

Goals:

- Support grouped figure generation as a first-class planning target.
- Assemble multiple source images into one master figure with panel labels, spacing, and export rules.
- Handle common academic montage cases such as four images merged into a single large figure.

Planned deliverables:

- Multi-panel figure schema in planned_payload. ✅ `planned_payload.panels` accepted with `render_route=composite_figure` for assembly.
- Panel layout presets and panel-label rules. ✅ Five layout presets (grid_2x2, horizontal_strip, vertical_strip, asymmetric_left, single_featured) and five label styles (uppercase, lowercase, numeric, roman, none) are available via `layout_preset` and `label_style` parameters.
- Composite assembly tool or route. ✅ `generate_figure` now supports a composite render route; `composite_figure` tool remains for direct calls.
- Single-output export for montage figures. ✅ Output is written as a single PNG with DPI metadata.

Mapped user requirements:

- Requirement 2: generate grouped figures.
- Requirement 3: generate stitched composite figures from multiple images.

### Theme 3: Poster Workflow

Status: shipped

Goals:

- Treat posters as a separate output class rather than just a large infographic.
- Support section-aware layouts, title bands, methods/results zones, figure placement, and citation areas.
- Make poster generation journal-aware or conference-aware where needed.

Planned deliverables:

- Poster asset_kind and planning route. ✅ `plan_poster` and `generate_poster` MCP tools with `asset_kind=poster`.
- Poster layout presets. ✅ Three presets: portrait_a0, landscape_a0, tri_column with conference-standard dimensions.
- Large-canvas export rules. ✅ Canvas size, DPI, and column count injected into generation prompt from preset config.
- Text-density and readability guardrails. ✅ `validate_poster_content` enforces title length, section count, and per-section character limits.

Mapped user requirements:

- Requirement 1: generate posters.

### Theme 4: Style Intelligence and Reuse

Status: shipped

Goals:

- Infer reusable style prompts from an existing image.
- Separate content semantics from reusable style semantics so the extracted style can be applied again.
- Turn image-derived style into a stored preset that can be reused across future jobs.

Planned deliverables:

- Style extraction workflow from an existing image. ✅ `extract_style` MCP tool analyses an image and returns a `StyleProfile` (color palette, typography, layout, mood).
- Reusable style prompt or style profile artifact. ✅ `StyleProfile` is persisted as JSON in `.academic-figures/styles/` and can be listed via `list_styles`.
- Style replay against new planned_payload jobs. ✅ `apply_style` MCP tool injects a stored style profile into any planned_payload and regenerates.

Mapped user requirements:

- Requirement 6: convert image elements into a reusable style prompt.

## Sequencing

1. Prompt persistence and replay. ✅
2. Journal retargeting for existing assets. ✅
3. Grouped figure planning and composite assembly. ✅ composite route + layout presets + label rules.
4. Poster-specific planning and export. ✅ plan_poster + generate_poster with guardrails.
5. Image-to-style extraction and reuse. ✅ extract_style + apply_style + list_styles.

## Out of Scope for This Roadmap

- Building a full academic literature search platform inside this repository.
- Replacing the single public renderer with multiple competing public creation APIs.
- Treating provider-specific prompt tricks as the source of truth instead of structured job metadata.
