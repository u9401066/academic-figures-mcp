# Asset-Aware MCP Codex Harness

These are workspace instructions for Codex when working with Asset-Aware MCP
through the VS Code extension, local CLI, or MCP server.

## Goal

Help the user build and operate citation-ready document workflows that preserve
precise evidence provenance for PDFs, DOCX files, tables, figures, DFM edits,
and LightRAG knowledge graph outputs.

## Working Style

- Use Traditional Chinese unless the user asks otherwise.
- Prefer exact file paths, command output summaries, and verification results.
- Treat messy document inputs as normal: broken numbering, mixed encodings,
  nested tables/lists, OCR artifacts, and repeated format conversions are all
  expected.
- When changing behavior, add a regression test that proves the edge case stays
  fixed.

## Core Workflow

1. Ingest or convert the document with the narrowest suitable MCP tool.
2. Preserve source identity with stable IDs, locator metadata, and hashes.
3. Keep DFM/DOCX round trips reversible and prompt before destructive writes.
4. Use CRAAP as a conservative evidence-quality scaffold; do not invent scores.
5. Prefer line/char/byte spans plus surrounding context for citation-ready
   claims.
6. Re-run the focused tests for changed code, then the full release harness
   before publishing.

## Repository Work

- Treat `.codex/skills`, `.cline/skills`, `.clinerules`, `.github/agents`, and
  `.github/copilot-instructions.md` as bundled assistant harness assets.
- Run `npm run sync-assets` in `vscode-extension/` before packaging the VSIX.
- Keep `vscode-extension/resources/repo-assets/**` synchronized with source
  files via `npm run sync-assets:check`.
- Preserve custom user MCP settings, Cline `alwaysAllow`, Codex comments, and
  unrelated server entries during extension install/update flows.

## Guardrails

- Never overwrite a source DOCX without checking stale mtime/session state.
- Never loosen citation locator integrity just to make a test pass.
- Do not commit generated outputs from `dist/`, `vscode-extension/out/`,
  `.venv/`, or document processing data directories.
- Keep the VSIX install path production-grade: native Copilot MCP provider,
  workspace `.vscode/mcp.json`, Cline MCP settings, Codex MCP config, and
  bundled harness assets must remain in sync.

## Related Files

- `.codex/skills/asset-aware-mcp-harness/SKILL.md`
- `.cline/skills/asset-aware-mcp-harness/SKILL.md`
- `.clinerules/workflows/full-check.md`
- `.clinerules/workflows/release-publish.md`
- `.github/copilot-instructions.md`
- `.github/agents/asset-aware-document.agent.md`
