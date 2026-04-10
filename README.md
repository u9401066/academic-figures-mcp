# 🎨 Academic Figures MCP

**Turn papers into publication-ready figures — for AI agents.**

An MCP server that lets AI agents (VS Code Copilot, Claude Code, OpenClaw, etc.) generate academic medical and scientific figures from PubMed IDs — with zero manual prompt engineering.

## Quick Start

```bash
pip install git+https://github.com/u9401066/academic-figures-mcp.git
```

## VS Code Copilot Setup

Add to your `.vscode/mcp.json` or Copilot MCP settings:
```json
{
  "servers": {
    "academic-figures": {
      "command": "pip",
      "args": ["run", "academic-figures-mcp"], // or direct path to installed binary
      "env": {
        "GOOGLE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

## 4 MCP Tools

| Tool | What it does |
|------|-------------|
| `generate_figure(pmid, figure_type)` | Fetches paper → builds 7-block prompt → generates publication-ready figure |
| `edit_figure(image_path, feedback)` | Natural language refinement: "箭頭換紅色", "標題字大一點" |
| `evaluate_figure(image_path)` | 8-domain quality scoring with actionable suggestions |
| `batch_generate(pmids)` | Generate figures for multiple papers at once |

## Usage Examples

Just tell your AI agent:
- "Generate a flowchart for PMID 41657234"
- "幫我做 PMID 41657234 的 consensus flowchart"
- "Make the arrows red and font bigger"
- "Generate figures for these 5 PMIDs"

## Architecture

```
┌──────────────┐     ┌───────────────────┐     ┌──────────────┐
│  AI Agent    │────▶│  MCP Server       │────▶│  Google      │
│  (Copilot,   │     │  (7-block prompt  │     │  Gemini 3.1  │
│   Claude, etc)│     │   orchestrator)   │     │  Flash Image │
└──────────────┘     └───────────────────┘     └──────────────┘
                            │
                     ┌──────▼──────┐
                     │  PubMed     │   Metadata & abstract
                     │  E-utilities│   fetch
                     └─────────────┘
```

## Features
- 📄 **Auto-fetch from PubMed** — Just give a PMID
- 🎯 **Smart figure typing** — Flowchart, mechanism, comparison, infographic
- 🏗️ **7-block prompt engine** — Structured prompts based on journal standards
- ✅ **Auto quality check** — 8-domain scoring, intelligent retry
- 🔄 **Natural language refinement** — "改一下顏色" → AI understands and re-renders
- 📊 **Batch mode** — Generate multiple figures at once
- 🔑 **One key** — Just Google Gemini API key needed

## Development

```bash
pip install -e .
python -m src.server
```
