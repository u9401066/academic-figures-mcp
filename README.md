# 🎨 Academic Figures MCP

**Turn papers into publication-ready figures — for AI agents.**

An agent-agnostic MCP server that transforms PubMed IDs into structured, journal-compliant medical and scientific figures using Google Gemini 3.1 Flash Image.

## Why This Exists

Generating academic figures normally requires:
1. Manual prompt engineering ✍️
2. Journal standard research 📚
3. Color code lookup 🎨
4. Quality self-review ✅
5. Retry loops 🔄

This MCP does all 5 steps automatically. Just give it a PMID.

## 4 MCP Tools

| Tool | Input | Output |
|------|-------|--------|
| `generate_figure` | `pmid`, `figure_type?` | 7-block prompt ready for Gemini API |
| `edit_figure` | `image_path`, `feedback` | Refined image via Gemini edit API |
| `evaluate_figure` | `image_path`, `figure_type?` | 8-domain scorecard with suggestions |
| `batch_generate` | `pmids: list`, `figure_type?` | Batch generation results |

## Quick Install

```bash
git clone https://github.com/u9401066/academic-figures-mcp.git
cd academic-figures-mcp
pip install -e .
export GOOGLE_API_KEY="your-key-here"
```

## Usage

### VS Code Copilot
Add to your Copilot MCP settings (`.vscode/mcp.json`):
```json
{
  "servers": {
    "academic-figures": {
      "command": "afm-server",
      "env": {
        "GOOGLE_API_KEY": "your-api-key"
      }
    }
  }
}
```

Then just ask:
- "Generate a flowchart for PMID 41657234"
- "幫我做 PMID 41657234 的 consensus flowchart"
- "What figure type should I use for PMID 34567890?"

### Claude Code / Cursor / Any MCP Host
Any MCP-compatible agent can use these tools directly.

## Architecture

```
┌──────────────────────┐
│  Your AI Agent       │     VS Code Copilot, Claude Code,
│  (Copilot, Claude,   │     OpenClaw, Hermes, etc.
│   any MCP host)      │
└──────────┬───────────┘
           │  MCP stdio
           ▼
┌──────────────────────────┐
│  Academic Figures MCP    │
│  ┌────────────────────┐  │
│  │ generate_figure    │  │
│  │ edit_figure        │  │  4 Tools
│  │ evaluate_figure    │  │
│  │ batch_generate     │  │
│  └────────┬───────────┘  │
│           │               │
│  ┌────────▼─────────────┐ │
│  │ Core Orchestrator    │ │
│  │                      │ │
│  │ 1. fetch_paper()     │ │  → PubMed E-utilities
│  │ 2. classify_type()   │ │  → Keyword + LLM analysis
│  │ 3. build_prompt()    │ │  → 7-block engine + templates
│  │ 4. generate_image()  │ │  → Google Gemini 3.1 Flash
│  │ 5. evaluate()        │ │  → 8-domain vision scoring
│  │ 6. retry()           │ │  → smart retry logic
│  └──────────────────────┘ │
└──────────────────────────┘
```

## Figure Types & Auto-Classification

The MCP auto-classifies papers into optimal figure types:

| Type | Best For | Example Papers |
|------|----------|----------------|
| **Flowchart** | Consensus, guidelines | "SSC 2026 Sepsis Guidelines" |
| **Mechanism** | Drug mechanisms, pathways | "Sugammadex encapsulation mechanism" |
| **Comparison** | RCTs, meta-analyses | "Crystalloid vs Colloid fluid resuscitation" |
| **Infographic** | Reviews, overviews | "Perioperative fasting consensus" |
| **Timeline** | Historical, longitudinal | "Evolution of general anesthesia" |
| **Anatomical** | Surgical techniques, blocks | "Regional anesthesia approaches" |
| **Data Visual** | PK/PD, dose-response | "Propofol PK modeling" |

## Knowledge Base (Included)

This repo ships with 8 curated reference documents:

| File | Content |
|------|---------|
| `prompt-templates.md` | 7-block prompt templates for 9 figure types |
| `anatomy-color-standards.md` | Medical illustration color coding reference |
| `journal-figure-standards.md` | Nature/Lancet formatting requirements |
| `gemini-tips.md` | Gemini 3.1 Flash prompt engineering best practices |
| `model-benchmark.md` | NB2 vs GPT Image 1.5 comparison data |
| `code-rendering.md` | matplotlib/Python figure generation reference |
| `scientific-figures-guide.md` | Scientific figure design principles |
| `ai-medical-illustration-evaluation.md` | 8-domain evaluation rubric |

## Development

```bash
pip install -e .
python -m src.server
```

## License

MIT

## Composite Engine (Multi-Panel Layout)

The `composite` module solves Gemini's weakness with multi-panel figures.
Instead of generating a single image with all panels (which often fails on
spatial layout, numbering, and mixed styles), it:

1. **Generates each panel independently** with focused prompts
2. **Composites them using Pillow** with precise pixel-level layout
3. **Programmatic text overlay** — 100% accurate labels, no misspellings

### Usage

```python
from src.composite import CompositeFigure, PanelSpec
from src.server import generate_figure

# Step 1: Generate panels separately
left = generate_figure(pmid="41657234", figure_type="anatomy")
right = generate_figure(pmid="41657234", figure_type="ultrasound")

# Step 2: Composite
comp = CompositeFigure()
comp.add_panel(
    PanelSpec(prompt="...", label="A", panel_type="anatomy"),
    left["image_path"]
)
comp.add_panel(
    PanelSpec(prompt="...", label="B", panel_type="ultrasound"),
    right["image_path"]
)
comp.set_title("Interscalene Brachial Plexus Block")
comp.set_citation("PMID 41657234 · Regional Anesthesia")
comp.compose("interscalene_block.pdf")
```

### MCP Tool: `composite_figure`

```
composite_figure(
    panels=[["left.png", "anatomy"], ["right.png", "ultrasound"]],
    labels=["A", "B"],
    title="..."
)
```

### Layout Specs

| Property | Value |
|----------|-------|
| Canvas | 2400 × 1600 px (8" × 5.33" @ 300 DPI) |
| Format | Double column (~183mm width, Nature standard) |
| Labels | A/B/C with pill-shaped background |
| Footer | Caption + PMIDs + citation |
| Divider | Vertical line between panels |
