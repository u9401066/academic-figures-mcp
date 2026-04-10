# Competitive Landscape

Updated: 2026-04-10

This document summarizes the latest GitHub MCP and web survey for academic-figure tooling around this repository.

## Direct Competitors

### SCIdrawer

Repository: JackaZhai/SCIdrawer

Why it matters:

- It is the closest public example of paper-to-scientific-figure generation rather than a generic image prompt app.
- It treats scientific content as structured input instead of only freeform prompting.
- It shows there is real demand for literature-grounded figure generation.

Why it is not the same product:

- It is not MCP-first.
- It is not centered on a reusable planning, validation, generation, evaluation, and iteration harness for multiple hosts.
- It does not package the workflow as a VS Code onboarding surface for non-engineers.

Practical conclusion:

- SCIdrawer is the closest benchmark for ambition, but not a drop-in replacement for this repo's MCP and workflow-harness positioning.

## Adjacent Wheels

### FigureFlow

Repository: maxschelski/figureflow

Useful because:

- It is strong on deterministic, publication-oriented figure assembly.
- It treats figures as reproducible layout artifacts instead of one-shot generated images.

Not the same because:

- It is a figure-composition tool, not an MCP agent harness.
- It does not solve PMID-driven planning, provider orchestration, or model-facing guardrails.

### Aut_Sci_Write

Repository: ShZhao27208/Aut_Sci_Write

Useful because:

- It shows how paper-grounded multi-step orchestration can be productized.
- It reinforces that academic workflows benefit from explicit intermediate structure.

Not the same because:

- It is broader scientific-writing automation, not a focused figure-generation runtime.

### pdffigures-mcp-server and pdffigures-style extractors

Repository example: vlln/pdffigures-mcp-server

Useful because:

- They help recover figure-caption pairs and existing visual artifacts from papers.
- They are good upstream retrieval components for citation checks, comparisons, or example mining.

Not the same because:

- They extract figures; they do not plan or generate new ones.

### pubmed-search-mcp

Repository: u9401066/pubmed-search-mcp

Useful because:

- It is already a full academic-search middleware layer rather than a thin PubMed wrapper.
- It covers unified search, PICO decomposition workflows, citation exploration, full-text retrieval, figure extraction, export, and research-timeline tooling.
- It is the strongest public reminder that search/discovery is its own product surface and should not be casually rebuilt inside a figure-generation repo.

Not the same because:

- Its center of gravity is literature discovery and research analysis, not publication-ready figure planning/generation.
- It helps agents find and analyze papers; it does not replace this repo's rendering routes, visual guardrails, or figure-edit/evaluate workflow.
- The right relationship is upstream or sidecar integration, not feature duplication.

### SciCap-related repos

Repository example: biodatlab/scicap-titipapa

Useful because:

- They are relevant for figure understanding, captioning, and evaluation data.
- They can inform automatic rubric design or training/evaluation datasets.

Not the same because:

- They are research assets, not an end-user generation harness.

## Strengths Worth Absorbing

### Deterministic rendering paths

Best source: FigureFlow and other layout-first tools

What to absorb:

- Prefer code-render or SVG routes for text-heavy, bilingual, or numerically exact figures.
- Keep editable intermediate artifacts instead of collapsing everything into bitmap output.
- Make multi-panel assembly reproducible.

Already landed in this repo:

- planner tool routing
- MCP validation layer
- batch parameter propagation
- Ollama-safe SVG fallback route for local usage

### Literature-grounded orchestration

Best source: SCIdrawer and paper-driven academic assistants

What to absorb:

- Keep PMID or paper metadata as a structured first-class input.
- Preserve paper traceability through planning and output metadata.
- Treat planning as its own step, not as invisible prompt text.

Already landed in this repo:

- dedicated plan_figure tool
- route recommendation before generation
- structured next-step payloads for MCP hosts

### Retrieval and evaluation support

Best source: pdffigures-style extractors and SciCap-style datasets

What to absorb:

- Use existing paper figures and captions as retrieval context.
- Build stronger automatic evaluation and citation checks.
- Add benchmarkable rubric datasets instead of only subjective review.

Good next steps:

- example retrieval from PubMed-linked sources
- citation-aware evaluation fixtures
- regression fixtures from real figure-caption pairs

### Search should stay externalized

Best source: pubmed-search-mcp

What to absorb:

- Treat rich literature discovery as an external capability with its own MCP boundary.
- Reuse upstream search outputs such as PMID lists, citation context, figure URLs, or full-text snippets instead of cloning the entire search stack locally.
- Keep this repo focused on converting structured paper context into figure plans, renders, edits, and evaluations.

Practical implication for this repo:

- The local PubMed client should remain a thin metadata fetcher for figure workflows.
- If richer retrieval is needed later, add an adapter to an external research-search MCP instead of re-implementing unified search, PICO, or citation-graph logic here.

## Core Differences We Should Not Copy Away

### Do not collapse into an API wrapper

The product should stay a guarded workflow harness. A thin provider wrapper loses the main differentiation.

### Do not force every request through bitmap generation

Charts, timelines, flowcharts, and text-heavy diagrams need exactness. They should be routed to deterministic or editable representations when appropriate.

### Do not hide guardrails only inside prompts

Validation belongs at the MCP boundary as typed input checks and route constraints, not only as instructions buried inside prompt prose.

### Do not tie the product story to one model vendor

Google, OpenRouter, and local runtimes are infrastructure choices. The stable value is the academic workflow, not the currently attached API.

### Do not become notebook-only or one-off CLI-only

The repo should remain hostable through MCP and usable from VS Code extension flows, because operational accessibility is part of the product value.

## Current Positioning Summary

The public ecosystem is not empty, but it is still sparse for the exact product shape of this repo.

- Direct paper-to-figure systems exist.
- Deterministic figure-composition tools exist.
- Figure extraction and captioning tools exist.
- An MCP-native academic figure planning and generation harness with validation, multi-route rendering, and VS Code onboarding is still uncommon.

That means this project is not building in a vacuum, but it also is not simply late to an already-settled category.
