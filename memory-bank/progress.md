# Progress (Updated: 2026-04-14)

## Done

- Fixed the VS Code local MCP launch path to use src.server so the FastMCP tool registry is not split across __main__ and src.presentation.server.
- Updated the workspace MCP settings migration so legacy academicFigures entries are rewritten to the canonical academic-figures entry while preserving envFile or env settings.
- Validated the fix with extension compile, extension-host smoke, and a real dev stdio MCP session that returned 11 tools and 2 prompts.

## Doing

- Preparing the verified MCP zero-tools fix for the v0.4.2 patch release.

## Next

- Reload the VS Code window or restart the Academic Figures MCP server after upgrading so VS Code reconnects to the fixed local runtime.
