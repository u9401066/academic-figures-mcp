# Roadmap

This roadmap tracks the next product capabilities for Academic Figures MCP beyond the current generic renderer, planning flow, and YAML-backed journal registry.

## Current Baseline

- One public generation contract centered on generic planned_payload rendering.
- MCP planning, generation, editing, evaluation, and batch workflows.
- YAML-backed journal requirement injection for Nature, Science, JAMA, NEJM, and Lancet.
- Direct-run support through afm-run for plan, generate, transform, and evaluate flows.

## Roadmap Themes

### Theme 1: Reproducibility and Retargeting

Status: next

Goals:

- Persist prompt packs and generation manifests so an output can be reproduced later.
- Retarget one existing image to a different journal profile without rebuilding the concept from zero.
- Keep journal conversion explainable by storing both the source prompt pack and the target journal constraints.

Planned deliverables:

- Saved job manifest per asset.
- Prompt and prompt-pack replay flow.
- Image-to-journal retargeting workflow.
- Before and after journal constraint diff in metadata.

Mapped user requirements:

- Requirement 4: maintain one image while switching journal requirements.
- Requirement 5: retain prompt for future regeneration.

### Theme 2: Multi-Panel and Composite Figures

Status: next

Goals:

- Support grouped figure generation as a first-class planning target.
- Assemble multiple source images into one master figure with panel labels, spacing, and export rules.
- Handle common academic montage cases such as four images merged into a single large figure.

Planned deliverables:

- Multi-panel figure schema in planned_payload.
- Panel layout presets and panel-label rules.
- Composite assembly tool or route.
- Single-output export for montage figures.

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

1. Prompt persistence and replay.
2. Journal retargeting for existing assets.
3. Grouped figure planning and composite assembly.
4. Poster-specific planning and export.
5. Image-to-style extraction and reuse.

## Out of Scope for This Roadmap

- Building a full academic literature search platform inside this repository.
- Replacing the single public renderer with multiple competing public creation APIs.
- Treating provider-specific prompt tricks as the source of truth instead of structured job metadata.
