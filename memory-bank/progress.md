# Progress (Updated: 2026-04-14)

## Done

- Fixed the VS Code local MCP launch path to use src.server so the FastMCP tool registry is not split across __main__ and src.presentation.server.
- Updated the workspace MCP settings migration so legacy academicFigures entries are rewritten to the canonical academic-figures entry while preserving envFile or env settings.
- Validated the fix with extension compile, extension-host smoke, and a real dev stdio MCP session that returned 11 tools and 2 prompts.
- Completed layer-decomposition technical specification (docs/spec-layer-decomposition.md) and strategic roadmap v2 (docs/roadmap-v2.md).
- Added Theme 5 (Layer-Aware Image Decomposition) to root ROADMAP.md with updated sequencing.
- **Spec v2 enhancement**: Added `LayerGroup` with hierarchical nesting (PPTX-like object grouping).
- **Spec v2 enhancement**: Added figure-type-aware segmentation strategies — flowchart two-pass hierarchical decomposition (structure → intra-node → connector binding).
- **Spec v2 enhancement**: Added `decomposition_depth` parameter (shallow/standard/deep) for granularity control.
- **Spec v2 enhancement**: Added PPTX export (promoted to Phase 1) with GroupShapes and editable TextBox shapes.
- **Spec v2 enhancement**: Added SVG export detail with `<g>` nesting and `<text>` elements.
- **Spec v2 enhancement**: Added `group`/`ungroup` edit actions and group-level operations.
- Updated roadmap-v2.md Phase 1 deliverables, competitive positioning, and value proposition.
- Updated ROADMAP.md Theme 5 with grouping, flowchart strategy, and PPTX capabilities.
- Updated memory bank (activeContext, decisionLog, progress).

## Doing

- Reviewing layer-decomposition spec v2 with grouping and flowchart strategy for PR merge.

## Next

- Implement Phase 1 layer decomposition: FigureScene/Layer/LayerGroup domain entities, GeminiSegmenter with flowchart strategy, FileSceneStore, PillowSceneRenderer, SVG/PPTX exporters, and MCP tools (v0.6.0).
