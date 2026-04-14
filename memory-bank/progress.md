# Progress (Updated: 2026-04-14)

## Done

- Extracted composite figure assembly into an application-level CompositeFigureUseCase and routed the MCP tool through DI instead of importing infrastructure directly.
- Added unit coverage for composite/edit/evaluate application flows, presentation validation helpers, and domain classifier/manifest round-trip behavior.
- Tightened DI container property return types to domain interfaces and resolved remaining mypy issues in manifest_store/composite infrastructure helpers.
- Added a tag-triggered publish workflow for PyPI Trusted Publisher and VS Code Marketplace packaging.
- Fixed repository and extension image assets that were JPEG payloads saved with `.png` filenames by converting the tracked files to true PNG assets.
- Hardened GeminiAdapter/edit output handling so generated image media types are inferred from actual bytes, preventing future fake-PNG regressions.
- Verified release readiness with focused regression tests, full Python validation, a real-provider smoke test, `uv build`, and VS Code extension packaging.
- Added a file-backed MetadataFetcher adapter, wired it through config and the DI container, and verified it with unit tests plus a real-provider smoke test using local YAML metadata.

## Doing

- Repository is validated for a new pre-tag pass; current work is deciding whether to add a sidecar/MCP metadata adapter next or freeze this tag with the file-backed adapter only.

## Next

- If needed, add a sidecar/MCP-backed metadata adapter above the same MetadataFetcher boundary; otherwise keep this tag focused and fix the VS Code Marketplace PAT before republishing.
