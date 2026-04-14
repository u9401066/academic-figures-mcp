# Active Context

## Current Goals

- Finalizing pre-tag hardening for academic-figures-mcp: keep release automation stable while making metadata retrieval pluggable through the existing MetadataFetcher boundary.
- Layer-aware image decomposition spec **v2** completed with hierarchical grouping (LayerGroup), figure-type-aware segmentation strategies (flowchart two-pass, mechanism, statistical), PPTX/SVG export, and decomposition_depth granularity control. Strategic roadmap v2 updated with grouping and PPTX capabilities.
- Next: implement Phase 1 domain entities (FigureScene, Layer, LayerGroup) and infrastructure adapters (GeminiSegmenter with flowchart strategy).

## Current Blockers

- No code blockers. Remaining release blocker is external: VS Code Marketplace still needs a valid VSCE PAT because that ecosystem does not support PyPI-style Trusted Publisher OIDC.

## Key Documents

- Technical spec v2: docs/spec-layer-decomposition.md (with LayerGroup, flowchart strategy, PPTX export)
- Strategic roadmap v2: docs/roadmap-v2.md (updated Phase 1 deliverables with grouping)
- Root roadmap: ROADMAP.md (Theme 5 updated with grouping and PPTX)
