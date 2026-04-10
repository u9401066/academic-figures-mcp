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
