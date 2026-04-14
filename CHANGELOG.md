# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, with repository history backfilled from the current documented state where practical.

## [Unreleased]

## [0.3.1]

### Added in 0.3.1

- Added a file-backed metadata adapter so planning and generation can read PMID records from local JSON/YAML files for offline demos, fixed corpora, and smoke tests.
- Added `AFM_METADATA_SOURCE`, `AFM_METADATA_FILE`, and `AFM_SMOKE_PMID` support for local metadata-driven smoke runs.
- Added workflow_dispatch inputs to [publish.yml](.github/workflows/publish.yml) so an existing tag can be republished without deleting and recreating tags.

### Changed in 0.3.1

- Kept metadata retrieval behind the existing `MetadataFetcher` interface while making the infrastructure implementation selectable through config.
- Updated release automation so VS Code Marketplace retries can target a specific tag and selected publish targets.

### Fixed in 0.3.1

- Prevented future provider image format regressions by inferring media type from actual image bytes instead of assuming `.png`.
- Hardened release validation with passing Ruff, mypy, pytest, and file-backed smoke test coverage before the next tag.

### Added

- Persisted generation manifests to `.academic-figures/manifests` with MCP tools for listing, replay, and journal retargeting (with before/after profile diffs).
- Added a composite render route so `generate_figure` can assemble `planned_payload.panels` into a single DPI-stamped montage.
- Added `AFM_MANIFEST_DIR` environment variable to relocate manifest storage.
- Added [ROADMAP.md](ROADMAP.md) to formalize the next capability tracks for posters, grouped figures, composite montage outputs, journal retargeting, prompt retention, and style extraction.
- Added this [CHANGELOG.md](CHANGELOG.md) so product and engineering changes are tracked in-repo instead of only living in Memory Bank notes.
- Added [scripts/start_afm_local.py](scripts/start_afm_local.py) as a cross-platform local launcher for Windows, macOS, and Linux.

### Changed

- Updated [README.md](README.md) to expose roadmap and changelog as first-class project documents.
- Replaced the workspace `.vscode/mcp.json` sample and extension-generated static MCP config with a shell-neutral `uv run --project ... python -m ...` launch shape.
- Converged direct PMID generation onto an internal plan-first bridge so `generate_figure` always renders from `planned_payload`, even when callers still use the legacy PMID input.
- Redrew [vscode-extension/resources/icon.svg](vscode-extension/resources/icon.svg) so the vector icon matches the newer PNG brand asset more closely.

## [0.3.0]

### Added in 0.3.0

- Added a generic planned_payload path to generate_figure so one public renderer can support PMID figures and non-PMID assets.
- Added planner emission of reusable planned_payload objects for downstream rendering.
- Added YAML-backed journal profiles and automatic prompt injection for Nature, Science, JAMA, NEJM, and Lancet.
- Added target_journal support in planning and generation flows.
- Added direct-run CLI support for payload-file generation and journal-aware execution.

### Changed in 0.3.0

- Repositioned the project around one public generation contract with harness tools around it.
- Expanded project documentation to reflect workflow-first positioning instead of API-wrapper positioning.

### Fixed in 0.3.0

- Brought the updated generation and journal-registry flows back to a green validation state with Ruff and pytest.
