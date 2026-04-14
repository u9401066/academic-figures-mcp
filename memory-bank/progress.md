# Progress (Updated: 2026-04-14)

## Done

- Extracted composite figure assembly into an application-level CompositeFigureUseCase and routed the MCP tool through DI instead of importing infrastructure directly.
- Added unit coverage for composite/edit/evaluate application flows, presentation validation helpers, and domain classifier/manifest round-trip behavior.
- Tightened DI container property return types to domain interfaces and resolved remaining mypy issues in manifest_store/composite infrastructure helpers.
- Added a tag-triggered publish workflow for PyPI Trusted Publisher and VS Code Marketplace packaging.
- Fixed repository and extension image assets that were JPEG payloads saved with `.png` filenames by converting the tracked files to true PNG assets.
- Hardened GeminiAdapter/edit output handling so generated image media types are inferred from actual bytes, preventing future fake-PNG regressions.
- Verified release readiness with focused regression tests, full Python validation, a real-provider smoke test, `uv build`, and VS Code extension packaging.

## Doing

- Repository is in a publish-ready validated state; current work is preparing segmented commits and release tag execution.

## Next

- Commit the validated changes in reviewable slices, push them to `main`, and create the release tag that triggers publish automation.
