# Layer-Aware Image Decomposition — Technical Specification

> Status: **RFC (Request for Comments)**
> Author: Academic Figures MCP Team
> Created: 2026-04-14
> Target release: v0.6.0 (Phase 1), v0.8.0 (Phase 2), v1.0.0 (Phase 3)

## 1. Problem Statement

### 1.1 Current Limitation

Academic Figures MCP currently generates **flat bitmap images**. Each output is a single-layer raster file (PNG/JPEG). When a user needs to adjust one element — move an arrow, resize a label, recolor a region — the entire figure must be regenerated or edited through natural language instructions to the image-edit API. This is:

- **Imprecise**: natural language edits cannot guarantee pixel-exact modifications.
- **Slow**: each edit triggers a full model inference round-trip.
- **Non-composable**: users cannot rearrange, recolor, or resize individual elements independently.

### 1.2 Competitive Pressure

Google NotebookLM (2026 refresh) now supports multi-step, multi-loop image generation from structured documents. The raw generation capability gap is closing. If Academic Figures MCP only offers "PMID → flat image", it risks becoming a thin wrapper with minimal differentiation.

### 1.3 Proposed Differentiator

**Post-generation layer decomposition**: after generating an academic figure, the system automatically segments the output into semantically meaningful, individually adjustable layer objects. Each layer is:

- **Named** (e.g., `title_bar`, `flow_arrow_3`, `panel_B_anatomy`)
- **Repositionable** (x, y offset)
- **Resizable** (scale, crop)
- **Re-stylable** (color, opacity, stroke)
- **Re-generable** (regenerate only this layer while keeping others fixed)

This transforms the output from a flat image into an **editable scene graph** — something no current academic-figure tool or NotebookLM provides.

## 2. Core Concepts

### 2.1 Layer

A layer is a rectangular region of the generated figure that corresponds to one semantic element. Each layer has:

| Field | Type | Description |
|-------|------|-------------|
| `layer_id` | `str` | Unique identifier within the figure |
| `label` | `str` | Human-readable semantic name |
| `category` | `LayerCategory` | Semantic type (see §2.2) |
| `bbox` | `BoundingBox` | Position and size in source image coords |
| `mask` | `bytes \| None` | Alpha mask for non-rectangular elements |
| `image_bytes` | `bytes` | Cropped/masked image data for this layer |
| `z_index` | `int` | Stacking order |
| `style` | `LayerStyle` | Editable visual properties |
| `parent_group_id` | `str \| None` | ID of the LayerGroup this layer belongs to (None = top-level) |
| `metadata` | `dict` | Free-form metadata (source prompt region, etc.) |

### 2.2 LayerCategory (Value Object)

```
background          — full-canvas background fill or pattern
title               — figure title text block
subtitle            — subtitle or section header
text_block          — body text, annotation, or footnote
label               — panel label (A, B, C) or axis label
arrow               — directional arrow or connector line
connector           — line, polyline, or curve linking two nodes (with optional mid-label)
flowchart_node      — a process / decision / terminal box in a flowchart
icon                — small symbolic element (drug icon, organ icon)
anatomical_region   — anatomical illustration area
data_chart          — chart, graph, or statistical plot
panel               — a complete sub-panel in a composite figure
border              — decorative border or frame element
legend              — figure legend or color key
citation            — PMID / reference text block
watermark           — overlay watermark or badge
group_frame         — invisible bounding frame for a LayerGroup (no own pixels)
```

### 2.3 LayerGroup (Value Object)

A `LayerGroup` bundles related layers into a logical unit — similar to "Group" in PowerPoint/PPTX, Figma, or SVG `<g>`. Groups can nest, forming a tree.

| Field | Type | Description |
|-------|------|-------------|
| `group_id` | `str` | Unique group identifier within the scene |
| `label` | `str` | Human-readable group name (e.g., `step_3_decision`) |
| `category` | `GroupCategory` | Semantic type (see §2.3.1) |
| `children` | `list[str]` | Ordered list of child `layer_id` or `group_id` values |
| `bbox` | `BoundingBox` | Union bounding box auto-computed from children |
| `collapsed` | `bool` | If `True`, the group is presented as a single opaque unit during editing |
| `metadata` | `dict` | Free-form metadata |

**Key rules:**

1. A `Layer` with `parent_group_id` set is a child of that group. A layer with `parent_group_id = None` is a top-level element.
2. Groups can contain other groups (nesting). Depth is capped at 4 levels to prevent runaway recursion.
3. **Group-level operations**: moving, scaling, or restyling a group applies the transform to every descendant. This mirrors the "select group → drag" interaction in PPTX.
4. `bbox` on a group is always the tightest rectangle enclosing all children. It is recomputed whenever a child moves or resizes.

#### 2.3.1 GroupCategory

```
flowchart_step      — a box + its inner text + outgoing connectors
flowchart_branch    — a decision diamond + yes/no labels + branch connectors
flowchart_swimlane  — a named column or row containing multiple steps
panel_group         — all layers belonging to one sub-panel
legend_group        — legend key items grouped together
annotation_cluster  — a set of callout lines + text labels pointing to one region
composite_block     — arbitrary user-defined grouping
```

### 2.4 FigureScene (Aggregate Root)

A `FigureScene` is the top-level domain entity that owns all layers for one generated figure.

| Field | Type | Description |
|-------|------|-------------|
| `scene_id` | `str` | Unique scene identifier |
| `source_manifest_id` | `str` | Link to the generation manifest that produced the original flat image |
| `canvas_width` | `int` | Original image width in px |
| `canvas_height` | `int` | Original image height in px |
| `layers` | `list[Layer]` | Ordered list of decomposed layers |
| `groups` | `list[LayerGroup]` | Hierarchical grouping of layers (may be empty) |
| `created_at` | `datetime` | Timestamp |
| `decomposition_model` | `str` | Model/method used for segmentation |
| `decomposition_confidence` | `float` | Overall segmentation quality score |

### 2.5 BoundingBox (Value Object)

```python
@dataclass(frozen=True)
class BoundingBox:
    x: int       # top-left x
    y: int       # top-left y
    width: int
    height: int
```

### 2.6 LayerStyle (Value Object)

```python
@dataclass(frozen=True)
class LayerStyle:
    opacity: float = 1.0
    rotation_deg: float = 0.0
    scale: float = 1.0
    fill_color: str | None = None
    stroke_color: str | None = None
    stroke_width: float | None = None
    font_size: float | None = None    # for text layers
    font_family: str | None = None    # for text layers
```

## 3. Architecture

### 3.1 Layer Placement in DDD

```
domain/
  entities.py          ← FigureScene, Layer, LayerGroup (new)
  value_objects.py     ← LayerCategory, GroupCategory, BoundingBox, LayerStyle (new)
  interfaces.py        ← ImageSegmenter, SceneStore (new ABCs)

application/
  decompose_figure.py  ← DecomposeFigureUseCase (new)
  edit_layer.py        ← EditLayerUseCase (new)
  recompose_scene.py   ← RecomposeSceneUseCase (new)

infrastructure/
  gemini_segmenter.py  ← Gemini vision-based segmentation (new)
  sam_segmenter.py     ← SAM2/GroundingDINO local segmentation (new, Phase 2)
  scene_store.py       ← File-backed scene persistence (new)
  scene_renderer.py    ← Pillow-based scene re-rendering (new)

presentation/
  tools.py             ← decompose_figure, edit_layer, recompose_scene (new MCP tools)
```

### 3.2 New Domain Interfaces

```python
@dataclass
class SegmentationResult:
    """Output of a segmentation pass: layers + optional groupings."""
    layers: list[Layer]
    groups: list[LayerGroup]   # may be empty for flat segmentation


class ImageSegmenter(ABC):
    """Segments a flat image into semantic layers."""

    @abstractmethod
    def segment(
        self,
        image_bytes: bytes,
        *,
        figure_type: str,
        language: str,
        expected_labels: list[str] | None = None,
    ) -> SegmentationResult: ...


class SceneStore(ABC):
    """Persists and retrieves FigureScene objects."""

    @abstractmethod
    def save(self, scene: FigureScene) -> FigureScene: ...

    @abstractmethod
    def load(self, scene_id: str) -> FigureScene: ...

    @abstractmethod
    def list(self, limit: int = 20) -> list[FigureScene]: ...


class SceneRenderer(ABC):
    """Re-renders a FigureScene into a flat image after layer edits."""

    @abstractmethod
    def render(self, scene: FigureScene) -> bytes: ...
```

### 3.3 Dependency Flow

```
Presentation (MCP tools)
    ↓
Application (DecomposeFigureUseCase, EditLayerUseCase, RecomposeSceneUseCase)
    ↓
Domain (FigureScene, Layer, ImageSegmenter interface, SceneStore interface)
    ↑
Infrastructure (GeminiSegmenter / SAMSegmenter, FileSceneStore, PillowSceneRenderer)
```

## 4. Segmentation Strategy

### 4.1 Phase 1 — Vision-Model Segmentation (Gemini)

Use Gemini's multimodal vision capabilities to identify and localize semantic regions:

1. Send the generated figure + a structured prompt describing the figure type and expected elements.
2. Ask Gemini to return a JSON array of detected regions with bounding boxes, labels, and categories.
3. Crop each region from the source image using Pillow.
4. Store as a `FigureScene`.

**Advantages**: No additional model infrastructure. Works with the existing Gemini adapter.

**Limitations**: Bounding boxes from vision models are approximate. No pixel-perfect masks.

### 4.2 Phase 2 — SAM2 / GroundingDINO Local Segmentation

Use SAM2 (Segment Anything Model 2) + GroundingDINO for precise segmentation:

1. Use Gemini (or local LLM) to identify semantic labels and approximate regions (Phase 1 output).
2. Feed labels + image into GroundingDINO for refined bounding boxes.
3. Feed refined boxes into SAM2 for pixel-perfect alpha masks.
4. Store each layer with both bbox and mask.

**Advantages**: Pixel-perfect masks. Supports non-rectangular elements (arrows, anatomical regions).

**Limitations**: Requires local GPU or remote inference endpoint. Adds ~2 new dependencies.

### 4.3 Phase 3 — Structured Generation (Native Layers)

Modify the generation pipeline to produce layered output natively:

1. Generate each semantic element as a separate image on transparent background.
2. Compose them into a scene graph during assembly (not after).
3. The user receives a pre-decomposed `FigureScene` with no post-hoc segmentation needed.

**Advantages**: Perfect layers. No segmentation error. Full editability from the start.

**Limitations**: Requires a fundamentally different generation contract. Higher generation cost (N calls instead of 1).

### 4.4 Figure-Type-Specific Strategies

Different academic figure types have fundamentally different structural properties. A single generic segmentation pass cannot handle all of them well. The segmenter must dispatch to **figure-type-aware strategies** that understand the expected layout grammar.

#### 4.4.1 Flowcharts / Clinical Guideline Diagrams

**Challenge**: Flowcharts contain many small, tightly-packed elements — boxes, decision diamonds, connector arrows, inline text labels, yes/no branch annotations, and sometimes swim-lane headers. A naïve bounding-box segmentation will either:

- **Over-merge**: treat a box + its text as one opaque blob (cannot edit text independently).
- **Over-split**: create 50+ micro-layers for every text run and line segment (unusable).

**Strategy: Two-pass hierarchical segmentation**

```
Pass 1 — Structure detection (coarse)
  → Identify nodes (process boxes, decision diamonds, terminators)
  → Identify connectors (arrows, lines) between nodes
  → Identify global elements (title, legend, footnotes)
  → Output: coarse layer list + spatial graph of node-connector relationships

Pass 2 — Intra-node decomposition (fine)
  → For each detected node, run a second segmentation:
      • Box border → border sub-layer
      • Inner text → text_block sub-layer(s)
      • Icon inside box (if any) → icon sub-layer
  → Automatically group into a LayerGroup (category: flowchart_step or flowchart_branch)

Pass 3 — Connector-to-group binding
  → For each connector layer, identify which two nodes it links
  → Store as metadata: { "from": "grp-step1", "to": "grp-step2" }
  → Optionally group connector + its mid-label into a child group
```

**Granularity knob**: The user can set `decomposition_depth`:

| Value | Behavior | Layer count (typical 8-step flowchart) |
|-------|----------|---------------------------------------|
| `shallow` | Each node is one opaque layer; connectors are separate | ~15–20 layers |
| `standard` (default) | Nodes decomposed into box + text; connectors separate | ~30–40 layers |
| `deep` | Every text run, line segment, and arrowhead is a layer | ~60–100 layers |

At `standard` depth, every node becomes a `LayerGroup` containing its box and text. This gives users PPTX-like control: drag the group to move a step, or expand the group to edit the text inside.

**Connector handling**: Connectors (arrows, lines) are special because they are thin, elongated, and often overlap with node borders. The segmenter should:

1. Detect connector paths as polyline/bezier coordinates, not just bounding boxes.
2. Store path geometry in `metadata.path_points` for accurate SVG/PPTX export.
3. When a connector has a text label (e.g., "Yes" / "No"), group the label with the connector.

#### 4.4.2 Mechanism / Pathway Diagrams

**Challenge**: Drug mechanism figures have overlapping regions — receptor icons sit on top of cell membranes, arrow cascades overlap with text annotations.

**Strategy**:
- Use z-index ordering from background (cell membrane) → foreground (receptor icons, drug molecules).
- Group: receptor + binding site + drug molecule → `annotation_cluster` group.
- Pathway arrows form chains; group sequential arrows into `composite_block`.

#### 4.4.3 Statistical / Data Visualization

**Challenge**: Charts have precise axes, gridlines, data points, and legends that are spatially dense.

**Strategy**:
- Treat axes + gridlines as a single `border` layer (not individually split).
- Each data series (bar group, line, scatter set) → one layer.
- Legend → `legend_group` with one sub-layer per legend entry.
- Title and axis labels → separate `text_block` layers.

#### 4.4.4 Anatomical Illustrations

**Challenge**: Overlapping regions (organs, tissue layers), callout lines radiating from one point.

**Strategy**:
- Each labelled anatomical region → `anatomical_region` layer with alpha mask (not bbox).
- Callout lines + their text → `annotation_cluster` group per callout.
- Background body outline → `background` layer.

#### 4.4.5 Composite / Multi-Panel Figures

**Strategy**:
- Top-level pass: detect each sub-panel → `panel` layer.
- Per-panel recursive segmentation: each panel is segmented independently using the appropriate figure-type strategy.
- Panel labels (A, B, C) → `label` layers grouped with their panel.

## 5. MCP Tool Surface

### 5.1 `decompose_figure`

```
decompose_figure(
    image_path: str,
    figure_type: str = "auto",
    language: str = "zh-TW",
    decomposition_depth: str = "standard",   # "shallow" | "standard" | "deep"
    expected_labels: list[str] | None = None,
    manifest_id: str | None = None,
) → FigureScenePayload
```

Segments a generated figure into layers and groups. If `manifest_id` is provided, links the scene to the original generation manifest for traceability. The `decomposition_depth` controls granularity (see §4.4.1).

**Returns**: Scene ID, list of layers with bounding boxes, list of groups, labels, categories, and confidence scores.

### 5.2 `edit_layer`

```
edit_layer(
    scene_id: str,
    layer_id: str,         # may also be a group_id for group-level operations
    action: str,
    params: dict,
) → LayerEditResult
```

**Actions**:

| Action | Params | Description |
|--------|--------|-------------|
| `move` | `dx`, `dy` | Translate layer (or group) position |
| `resize` | `scale` or `width`, `height` | Scale or resize |
| `restyle` | `opacity`, `fill_color`, `stroke_color`, etc. | Change visual properties |
| `replace` | `prompt`, `model` | Regenerate this layer's content |
| `remove` | — | Remove layer (or group and all children) from scene |
| `duplicate` | `new_label` | Clone layer (or group) |
| `reorder` | `z_index` | Change stacking order |
| `group` | `target_ids: list[str]` | Create a new LayerGroup from the specified layers |
| `ungroup` | — | Dissolve a group, promoting children to top level |

### 5.3 `recompose_scene`

```
recompose_scene(
    scene_id: str,
    output_path: str | None = None,
    format: str = "png",
) → RecomposeResult
```

Re-renders the full scene into a flat image after layer edits.

### 5.4 `list_scenes`

```
list_scenes(limit: int = 20) → list[SceneSummary]
```

Lists recent decomposed scenes for continued editing.

### 5.5 `export_scene`

```
export_scene(
    scene_id: str,
    format: str = "svg",
    output_path: str | None = None,
    group_mode: str = "preserve",   # "preserve" | "flatten"
) → ExportResult
```

Exports the scene to an editable format. `group_mode` controls whether groups are preserved in the output:

- **`preserve`** (default): groups map to container structures in the target format.
- **`flatten`**: dissolve all groups; each layer is a top-level element.

**Supported formats:**

| Format | Extension | Groups | Text editability | Notes |
|--------|-----------|--------|------------------|-------|
| `svg` | `.svg` | `<g>` nesting | `<text>` elements for text layers | Primary. Opens in Inkscape/Illustrator/browsers. |
| `pptx` | `.pptx` | Slide groups (`<p:grpSp>`) | Editable text shapes | PPTX slide with grouped shapes. Each layer → shape; each group → grouped shapes. Uses `python-pptx`. |
| `psd` | `.psd` | Layer groups | Rasterized text | Best-effort via `psd-tools`. Opens in Photoshop. |
| `figma-json` | `.json` | Figma frame hierarchy | N/A (import as frames) | Future. Figma-importable JSON. |

#### 5.5.1 PPTX Export Details

PPTX export maps the scene graph to a PowerPoint slide:

```
FigureScene
  └── Slide (canvas_width × canvas_height scaled to slide dimensions)
       ├── background layer → slide background image
       ├── LayerGroup "grp-step1" → <p:grpSp> (GroupShape)
       │    ├── step1-box → Rectangle shape with fill
       │    └── step1-text → TextBox shape with editable text
       ├── connector-1 → Connector shape (arrow/line)
       ├── title layer → TextBox shape
       └── ...
```

**Why PPTX?** Academic users frequently embed figures into PowerPoint presentations. Exporting as an editable PPTX slide — with grouped shapes that can be ungrouped, edited, and restyled — is a natural handoff format. This is the "類似像 PPTX 那樣" capability the product needs.

**Text layer handling**: When a layer has `category` in (`title`, `subtitle`, `text_block`, `label`, `citation`), the exporter attempts **OCR-or-prompt-based text extraction** to create a genuine editable `TextBox` shape rather than an embedded image. Fallback: embed the layer's raster image as a picture shape.

**Connector handling**: Connector layers with `metadata.path_points` are exported as PPTX connector shapes with begin/end anchors linked to their source/target node shapes. This preserves the "drag node → connector follows" behavior in PowerPoint.

#### 5.5.2 SVG Export Details

SVG export maps groups to `<g>` elements with `id` and `data-category` attributes:

```xml
<svg viewBox="0 0 2400 1600" xmlns="http://www.w3.org/2000/svg">
  <g id="grp-main-flow" data-category="composite_block">
    <g id="grp-step1" data-category="flowchart_step">
      <rect id="step1-box" x="800" y="200" width="400" height="120" fill="#E3F2FD"/>
      <text id="step1-text" x="820" y="260" font-size="14">Patient Assessment</text>
    </g>
    <line id="connector-1-2" x1="1000" y1="320" x2="1000" y2="400"
          stroke="#333" marker-end="url(#arrowhead)"/>
  </g>
</svg>
```

Text layers become `<text>` elements (editable in Inkscape). Image-based layers become `<image>` elements with embedded base64 or external file references.

## 6. User Workflows

### 6.1 Generate → Decompose → Edit → Recompose

```
User: plan_figure(pmid="12345678")
Agent: [returns plan with figure_type=mechanism]

User: generate_figure(planned_payload=...)
Agent: [generates flat figure → figure.png]

User: decompose_figure(image_path="figure.png", manifest_id="m-abc")
Agent: [returns scene with 8 layers:
         title_bar, background, arrow_1, arrow_2,
         drug_icon, receptor_icon, label_mechanism, citation]

User: edit_layer(scene_id="s-xyz", layer_id="arrow_1", action="restyle",
                  params={"stroke_color": "#FF0000"})
Agent: [arrow_1 is now red]

User: edit_layer(scene_id="s-xyz", layer_id="title_bar", action="move",
                  params={"dx": 0, "dy": -20})
Agent: [title moved up 20px]

User: recompose_scene(scene_id="s-xyz", output_path="figure_v2.png")
Agent: [renders final composite]
```

### 6.2 Generate → Decompose → Export to External Editor

```
User: decompose_figure(image_path="figure.png")
User: export_scene(scene_id="s-xyz", format="svg")
Agent: [writes figure_layers.svg with each layer as a <g> element]
```

User can now open in Inkscape, Illustrator, or Figma for fine-grained editing.

### 6.3 Selective Layer Regeneration

```
User: edit_layer(scene_id="s-xyz", layer_id="drug_icon",
                  action="replace",
                  params={"prompt": "3D molecular structure of aspirin, white background"})
Agent: [regenerates only the drug icon, keeps all other layers intact]

User: recompose_scene(scene_id="s-xyz")
Agent: [renders new composite with updated drug icon]
```

## 7. Data Persistence

### 7.1 Scene Storage Format

Scenes are stored under `.academic-figures/scenes/` as JSON + layer image files:

```
.academic-figures/scenes/
  s-abc123/
    scene.json          ← FigureScene metadata
    layer-title.png     ← cropped title layer image
    layer-arrow-1.png   ← cropped arrow layer image
    layer-drug-icon.png
    ...
```

### 7.2 Scene JSON Schema

```json
{
  "scene_id": "s-abc123",
  "source_manifest_id": "m-xyz789",
  "canvas_width": 2400,
  "canvas_height": 1600,
  "decomposition_model": "gemini-2.5-pro",
  "decomposition_confidence": 0.87,
  "created_at": "2026-04-14T12:00:00Z",
  "layers": [
    {
      "layer_id": "title-bar",
      "label": "Figure Title",
      "category": "title",
      "bbox": {"x": 100, "y": 20, "width": 2200, "height": 60},
      "z_index": 10,
      "style": {"opacity": 1.0, "font_size": 36},
      "parent_group_id": null,
      "image_file": "layer-title.png",
      "mask_file": null
    },
    {
      "layer_id": "step1-box",
      "label": "Step 1: Patient Assessment",
      "category": "flowchart_node",
      "bbox": {"x": 800, "y": 200, "width": 400, "height": 120},
      "z_index": 5,
      "style": {"opacity": 1.0, "fill_color": "#E3F2FD"},
      "parent_group_id": "grp-step1",
      "image_file": "layer-step1-box.png",
      "mask_file": null
    },
    {
      "layer_id": "step1-text",
      "label": "Assessment criteria text",
      "category": "text_block",
      "bbox": {"x": 820, "y": 220, "width": 360, "height": 80},
      "z_index": 6,
      "style": {"opacity": 1.0, "font_size": 14},
      "parent_group_id": "grp-step1",
      "image_file": "layer-step1-text.png",
      "mask_file": null
    }
  ],
  "groups": [
    {
      "group_id": "grp-step1",
      "label": "Step 1 — Patient Assessment",
      "category": "flowchart_step",
      "children": ["step1-box", "step1-text"],
      "bbox": {"x": 800, "y": 200, "width": 400, "height": 120},
      "collapsed": false,
      "metadata": {}
    },
    {
      "group_id": "grp-main-flow",
      "label": "Main flowchart path",
      "category": "composite_block",
      "children": ["grp-step1", "grp-step2", "connector-1-2"],
      "bbox": {"x": 200, "y": 200, "width": 1800, "height": 1200},
      "collapsed": false,
      "metadata": {}
    }
  ]
}
```

## 8. Quality Gates

### 8.1 Decomposition Quality Score

After segmentation, the system computes a decomposition quality score:

| Criterion | Weight | Measurement |
|-----------|--------|-------------|
| Coverage | 30% | % of image pixels assigned to at least one layer |
| Overlap | 20% | % of pixels assigned to >1 layer (lower is better) |
| Label match | 25% | % of expected_labels that appear in layer labels |
| Category diversity | 15% | # unique categories found vs. expected for figure_type |
| Confidence spread | 10% | Mean confidence of individual layer detections |

If the score falls below a configurable threshold (default 0.7), the system warns the user and suggests manual adjustment or Phase 2 segmentation.

### 8.2 Recompose Fidelity Check

After recomposition, the system can optionally compare the re-rendered image against the original to detect:

- Missing regions (layer gaps)
- Color drift (from style edits)
- Alignment errors (from position edits)

## 9. Phased Delivery

### Phase 1 — Vision-Model Decomposition (v0.6.0)

**Goal**: Ship the core decompose → edit → recompose loop using Gemini vision, with grouping and PPTX export.

Deliverables:
- `FigureScene`, `Layer`, `LayerGroup` domain entities
- `LayerCategory`, `GroupCategory`, `BoundingBox`, `LayerStyle` value objects
- `ImageSegmenter` interface + `GeminiSegmenter` implementation (with figure-type-aware strategies)
- `SceneStore` interface + `FileSceneStore` implementation
- `SceneRenderer` interface + `PillowSceneRenderer` implementation
- `DecomposeFigureUseCase`, `EditLayerUseCase`, `RecomposeSceneUseCase`
- MCP tools: `decompose_figure`, `edit_layer`, `recompose_scene`, `list_scenes`
- `export_scene` MCP tool — SVG and PPTX export (groups preserved)
- Flowchart two-pass hierarchical segmentation strategy (§4.4.1)
- `decomposition_depth` parameter (`shallow` / `standard` / `deep`)
- `group` / `ungroup` edit actions
- Unit tests for domain types and use cases
- Integration test for end-to-end decompose → edit → recompose flow

### Phase 2 — Precision Segmentation (v0.8.0)

**Goal**: Add pixel-perfect masks, non-rectangular layer support, and PSD export.

Deliverables:
- `SAMSegmenter` infrastructure adapter (SAM2 + GroundingDINO)
- Alpha mask support in Layer and SceneRenderer
- PSD export format in `export_scene`
- Decomposition quality gate automation
- Configurable segmenter selection (Gemini vs. SAM) via provider config
- CJK text-layer special handling
- Scene version history (undo support)

### Phase 3 — Native Layered Generation (v1.0.0)

**Goal**: Generate figures as pre-decomposed scene graphs, eliminating post-hoc segmentation.

Deliverables:
- Modified generation pipeline that produces per-element images
- Automatic scene assembly during generation
- Layer-aware planning (planner recommends layer structure with group hierarchy)
- Recompose fidelity check
- Figma-JSON export format

## 10. Dependencies and Risks

### 10.1 New Dependencies (Phase 2)

| Package | Purpose | License |
|---------|---------|---------|
| `segment-anything-2` | Pixel-perfect segmentation | Apache 2.0 |
| `groundingdino` | Open-set object detection | Apache 2.0 |
| `psd-tools` | PSD export | MIT |
| `python-pptx` | PPTX export with grouped shapes and editable text | MIT |

Phase 1 requires **no new dependencies** — it uses existing Gemini + Pillow.

> Note: `python-pptx` may be introduced in Phase 1 if PPTX export is prioritized. It is a pure-Python library with no native dependencies.

### 10.2 Risk Matrix

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Gemini vision bbox accuracy too low | High | Medium | Fall back to grid-based decomposition; accelerate Phase 2 |
| SAM2 GPU requirement excludes CI/CD | Medium | High | Keep SAM as optional extra; CI tests use Gemini path |
| Layer edits introduce visual artifacts | Medium | Medium | Recompose fidelity check + user preview before save |
| Generation cost increase (Phase 3) | Medium | High | Make native-layer generation opt-in; keep flat path as default |
| CJK text layers lose fidelity on crop | Medium | Medium | Use text-detection-specific segmentation for CJK labels |
| Flowchart over-segmentation (deep mode) | Medium | Medium | Default to `standard` depth; warn when layer count > 80 |
| PPTX connector anchoring inaccuracy | Low | Medium | Fall back to free-floating line shapes when anchor detection fails |
| Group nesting exceeds export format limits | Low | Low | Cap at 4 levels; flatten deeper nests on export |

## 11. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Mean decomposition coverage | ≥ 85% | % image pixels in ≥1 layer |
| Mean label match rate | ≥ 90% | expected_labels found in layers |
| Edit → recompose round-trip time | < 3s | Time from edit_layer to recompose_scene (no regen) |
| User layer edit satisfaction | ≥ 4/5 | Surveyed rating on precision of edits |
| Export compatibility | SVG, PPTX, PSD | Opens correctly in Inkscape, PowerPoint, Photoshop |

## 12. Relationship to Existing Features

| Existing Feature | Relationship |
|-----------------|--------------|
| `generate_figure` | Upstream: produces the flat image that decompose consumes |
| `edit_figure` | Parallel: NL-based whole-image edit remains for simple changes; layer edit for precision |
| `multi_turn_edit` | Parallel: multi-turn NL edit for iterative whole-image; layer edit for targeted |
| `composite_figure` | Complementary: composite assembles from multiple sources; decompose breaks one source into layers |
| `verify_figure` | Downstream: verify can run on recomposed output |
| `replay_manifest` | Linked: scene stores manifest_id for provenance |
| `evaluate_figure` | Downstream: 8-domain evaluation runs on recomposed output |

## 13. Open Questions

1. **Should decomposition be automatic after every generation?** Or explicitly triggered by the user? Current recommendation: explicit trigger via `decompose_figure`, with an option to auto-decompose via a `decompose_after_generate=true` flag on `generate_figure`.

2. **What is the minimum useful layer count?** If Gemini can only reliably detect 3-4 major regions, is that still valuable? Current recommendation: yes, even coarse decomposition (background + content regions + text) enables useful edits.

3. **Should layer edits be version-controlled?** Each edit creates a new scene version, enabling undo. Current recommendation: yes, store as `scene-v1.json`, `scene-v2.json`, etc.

4. **PSD export feasibility on all platforms?** `psd-tools` is pure Python but the format is complex. Current recommendation: SVG as primary export, PSD as best-effort.

5. **Can Gemini Vision reliably produce group hierarchies for flowcharts?** Early experiments needed. If Gemini returns only flat bounding boxes, the grouping heuristic must infer groups from spatial proximity (box-contains-text → group, arrow-endpoint-near-box → link). Phase 1 fallback: spatial-proximity grouping algorithm in `GeminiSegmenter`.

6. **PPTX connector shape accuracy?** `python-pptx` supports connector shapes but anchor positioning is fragile. Alternative: render connectors as line shapes (not true connectors) with arrowhead markers. Revisit once prototype validates.

7. **Should `decomposition_depth` be per-figure-type?** A flowchart may need `standard` while a simple bar chart only needs `shallow`. Current recommendation: allow per-call override, but each figure-type strategy has a sensible default.

8. **Text extraction for PPTX text shapes**: should we use OCR (Tesseract / Gemini vision) or store the original prompt text? Current recommendation: prefer prompt-derived text when available (from `planned_payload`), fall back to Gemini-based text recognition.

---

*This specification is a living document. Update as implementation progresses and design decisions are finalized.*
