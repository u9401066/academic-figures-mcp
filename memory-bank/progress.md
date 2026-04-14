# Progress (Updated: 2026-04-14)

## Done

- Added an offline stub image provider plus package smoke that plans, generates, verifies, and writes manifests/images without real provider keys, keeping macOS/Windows/Linux CI green.
- Fixed the VS Code local MCP launch path to use src.server so the FastMCP tool registry is not split across __main__ and src.presentation.server.
- Updated the workspace MCP settings migration so legacy academicFigures entries are rewritten to the canonical academic-figures entry while preserving envFile or env settings.
- Validated the fix with extension compile, extension-host smoke, and a real dev stdio MCP session that returned 11 tools and 2 prompts.

## Doing

- Documenting CI/package-smoke coverage and confirming the multi-OS matrix is green after the stub provider changes.

## Next

- Run the refreshed package smoke in CI and tag the next patch release once cross-platform checks stay green.
