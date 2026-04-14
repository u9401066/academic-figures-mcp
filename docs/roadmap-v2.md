# Academic Figures MCP — Strategic Roadmap v2

> Updated: 2026-04-14
> Scope: This document defines the product trajectory from v0.4 (current) through v1.0, with layer-aware image decomposition as the central differentiator.

## Executive Summary

Academic Figures MCP has shipped a working multi-step academic figure workflow: PMID ingestion → planning → generation → evaluation → iteration, with journal retargeting, prompt replay, composite assembly, and VS Code extension packaging.

However, the raw generation capability gap between this project and Google NotebookLM's updated multi-step image generation is closing. **Flat bitmap output is no longer a defensible moat.**

The next phase repositions the product around a capability that no current tool provides: **post-generation layer decomposition** — transforming a generated academic figure into an editable scene graph of individually adjustable layer objects.

This gives researchers something NotebookLM, SCIdrawer, and FigureFlow cannot: generate once, edit precisely, export as editable layers.

## Competitive Positioning

| Capability | NotebookLM (2026) | SCIdrawer | FigureFlow | AFM v0.4 | AFM v1.0 (target) |
|-----------|:-:|:-:|:-:|:-:|:-:|
| Multi-step generation | ✅ | ✅ | ❌ | ✅ | ✅ |
| PMID-driven planning | ❌ | ✅ | ❌ | ✅ | ✅ |
| Journal-aware constraints | ❌ | ❌ | ❌ | ✅ | ✅ |
| MCP-native agent interface | ❌ | ❌ | ❌ | ✅ | ✅ |
| Multi-turn editing | ❌ | ❌ | ❌ | ✅ | ✅ |
| Quality gate / verification | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Layer decomposition** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Per-layer editing** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Object grouping (PPTX-like)** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Flowchart-aware segmentation** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **SVG/PPTX/PSD export** | ❌ | ❌ | ✅ (code) | ❌ | ✅ |
| **Native layered generation** | ❌ | ❌ | ❌ | ❌ | ✅ |

## Roadmap Phases

### Phase 0: Foundation Hardening (v0.4.x → v0.5.0) — Current

**Status**: In progress

**Theme**: Finish composite-figure planning, stabilize release automation, close out existing roadmap items.

| Deliverable | Status |
|-------------|--------|
| Composite render route via DDD path | ✅ Shipped |
| Panel layout presets and label rules | ⏳ In progress |
| Grouped figure planning schemas | ⏳ In progress |
| Package smoke tests (uvx path) | ✅ Shipped |
| VS Code extension MCP launch fix | ✅ Shipped |
| File-backed metadata fetcher | ✅ Shipped |
| Release automation (PyPI OIDC + VSX) | ✅ Shipped |

**Exit criteria**: All Theme 2 (Multi-Panel) deliverables complete. CI green. v0.5.0 tag.

---

### Phase 1: Vision-Model Layer Decomposition (v0.5.0 → v0.6.0)

**Status**: Planned — the core differentiator begins here.

**Theme**: Generate a flat figure, then decompose it into editable layers **with hierarchical grouping** using Gemini vision. Export to SVG and PPTX for professional editing.

**Technical Spec**: [`docs/spec-layer-decomposition.md`](spec-layer-decomposition.md)

| Deliverable | Priority | Notes |
|-------------|----------|-------|
| `FigureScene`, `Layer`, `LayerGroup` domain entities | P0 | Hierarchical scene graph with group nesting (spec §2.1–2.4) |
| `LayerCategory`, `GroupCategory`, `BoundingBox`, `LayerStyle` value objects | P0 | Includes `flowchart_node`, `connector`, `group_frame` categories |
| `ImageSegmenter` domain interface | P0 | Returns `SegmentationResult` (layers + groups) |
| `GeminiSegmenter` infrastructure adapter | P0 | Figure-type-aware strategies (spec §4.4) |
| Flowchart two-pass hierarchical segmentation | P0 | Structure detection → intra-node decomposition → connector binding (spec §4.4.1) |
| `decomposition_depth` parameter | P0 | `shallow` / `standard` / `deep` granularity knob |
| `FileSceneStore` infrastructure adapter | P0 | JSON + cropped PNGs; stores groups in scene JSON |
| `PillowSceneRenderer` infrastructure adapter | P0 | Re-renders scene from layers respecting group z-order |
| `DecomposeFigureUseCase` | P0 | Core use case with figure-type dispatch |
| `EditLayerUseCase` | P0 | move, resize, restyle, remove, reorder + **group, ungroup** |
| `RecomposeSceneUseCase` | P0 | Flatten scene back to image |
| MCP tools: `decompose_figure`, `edit_layer`, `recompose_scene`, `list_scenes` | P0 | Thin presentation handlers |
| `export_scene` MCP tool — SVG export | P0 | Groups → `<g>` elements; text → `<text>` elements (spec §5.5.2) |
| `export_scene` MCP tool — PPTX export | P0 | Groups → PPTX GroupShapes; text → TextBox shapes (spec §5.5.1) |
| Decomposition quality score | P1 | Coverage + overlap + label match |
| Unit tests for domain types | P0 | |
| Integration test: decompose → edit → recompose | P1 | |
| Selective layer regeneration (`replace` action) | P1 | Regen one layer via Gemini |

**Exit criteria**: A user can generate a flowchart, decompose it into grouped layers (each box + text = one group), edit individual layers or whole groups (PPTX-like), recompose, and export to SVG or PPTX with preserved grouping. MCP tools work end-to-end. Unit + integration tests pass.

**New dependencies**: `python-pptx` (MIT, pure Python, no native deps).

---

### Phase 2: Precision Segmentation and Advanced Export (v0.6.0 → v0.8.0)

**Status**: Discovery

**Theme**: Pixel-perfect masks, non-rectangular layers, PSD export, and enhanced connector fidelity.

| Deliverable | Priority | Notes |
|-------------|----------|-------|
| `SAMSegmenter` adapter (SAM2 + GroundingDINO) | P0 | Optional extra; Gemini path remains default |
| Alpha mask support in Layer + SceneRenderer | P0 | Non-rectangular elements (arrows, anatomical regions) |
| PSD export via `psd-tools` | P1 | Best-effort Photoshop compat with layer groups |
| PPTX connector anchoring refinement | P1 | True connector shapes with begin/end anchors |
| Decomposition quality gate automation | P1 | Warn below threshold |
| Configurable segmenter selection | P1 | Provider config: `gemini` vs `sam` |
| CJK text-layer special handling | P1 | Text detection before crop; OCR fallback for PPTX text |
| Scene version history (undo support) | P2 | `scene-v1.json`, `scene-v2.json` |

**Exit criteria**: Pixel-perfect layer masks for non-rectangular elements. PSD export opens correctly in Photoshop with layer groups. Quality gate warns on low-confidence decomposition.

**New dependencies**: `segment-anything-2` (optional), `groundingdino` (optional), `psd-tools` (optional).

---

### Phase 3: Native Layered Generation (v0.8.0 → v1.0.0)

**Status**: Discovery

**Theme**: Eliminate post-hoc segmentation by generating figures as layered scene graphs from the start.

| Deliverable | Priority | Notes |
|-------------|----------|-------|
| Per-element generation pipeline | P0 | Generate each semantic element separately on transparent BG |
| Automatic scene assembly during generation | P0 | Compose layers into FigureScene during generation, not after |
| Layer-aware planning | P0 | Planner recommends layer structure, group hierarchy, and element list |
| Recompose fidelity check | P1 | Compare recomposed vs. flat-generated for drift |
| Figma-JSON export format | P2 | Import directly into Figma |
| Layer-aware journal retargeting | P1 | Retarget per-layer styles to new journal profile |
| Layer template presets | P2 | Pre-built layer structures for common figure types |

**Exit criteria**: A user can plan a figure, generate it as a pre-decomposed scene graph, edit individual layers, and export. No post-hoc segmentation needed for the native path. Flat generation remains as a fast-path option.

**New dependencies**: TBD based on implementation approach.

---

### Parallel Track: Poster Workflow (v0.7.0)

**Status**: Planned (from original roadmap Theme 3)

**Theme**: First-class poster output with section-aware layout.

This track can proceed in parallel with Phase 2 and benefits from layer decomposition: poster sections map naturally to layers.

| Deliverable | Priority |
|-------------|----------|
| Poster `asset_kind` and planning route | P0 |
| Poster layout presets (A0, A1, etc.) | P0 |
| Section-aware zones (title, methods, results, figures, citations) | P0 |
| Large-canvas export rules | P1 |
| Text-density and readability guardrails | P1 |
| Layer-decomposed poster output | P1 |

---

### Parallel Track: Style Intelligence (v0.9.0)

**Status**: Discovery (from original roadmap Theme 4)

**Theme**: Extract and reuse visual styles across figures.

Layer decomposition enhances style extraction: styles can be extracted per-layer-category instead of from the whole image.

| Deliverable | Priority |
|-------------|----------|
| Style extraction from existing image | P0 |
| Per-layer-category style extraction | P1 |
| Reusable style profile artifact | P0 |
| Style replay against new planned_payload | P0 |
| Style transfer across figure types | P2 |

## Sequencing Summary

```
v0.4.x  ── Foundation hardening, multi-panel completion
  │
v0.5.0  ── Multi-panel + grouped planning complete
  │
v0.6.0  ── ★ Layer decomposition (Gemini vision) — THE DIFFERENTIATOR
  │
v0.7.0  ── Poster workflow (parallel track)
  │
v0.8.0  ── Precision segmentation (SAM2) + editable export
  │
v0.9.0  ── Style intelligence + per-layer style extraction
  │
v1.0.0  ── ★ Native layered generation — full scene-graph pipeline
```

## Value Proposition After v1.0

When complete, Academic Figures MCP will be the only tool that provides:

1. **PMID → planned academic figure** (existing moat)
2. **Flat image → editable layer scene graph with hierarchical grouping** (new moat, Phase 1)
3. **Per-layer and per-group precision editing** via MCP — like PPTX object editing but for academic figures (new moat, Phase 1)
4. **Figure-type-aware decomposition** — flowchart nodes auto-grouped, connectors linked, statistical series isolated (new moat, Phase 1)
5. **SVG and PPTX export** with preserved grouping for handoff to professional editors and presentations (new moat, Phase 1)
6. **Pixel-perfect segmentation** for non-rectangular academic elements (Phase 2)
7. **PSD export** for Photoshop workflows (Phase 2)
8. **Native layered generation** eliminating post-hoc segmentation entirely (Phase 3)
9. **Journal-aware layer-level retargeting** (Phase 3)

This transforms the product from "an academic image generator" into "an academic figure editor with AI generation built in" — a fundamentally different and more defensible category. The PPTX-like grouping model makes it immediately familiar to academic users who already think in PowerPoint.

## Out of Scope

- Building a full vector editor UI (Figma/Illustrator replacement). The product stays as an MCP harness + VSX surface.
- Real-time collaborative editing of scenes. Scenes are single-user artifacts.
- Video or animation output. Scope is static publication figures.
- Training custom segmentation models. We use off-the-shelf models (Gemini vision, SAM2).

---

*This roadmap is a living document. Update as phases ship and market conditions evolve.*
