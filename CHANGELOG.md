# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, with repository history backfilled from the current documented state where practical.

## [Unreleased]

## [0.4.5]

### Added in 0.4.5

- Added the code-only `prepare_publication_image` MCP/CLI route for Pillow-based 600 DPI publication delivery without invoking any image-generation provider.
- Added OpenAI `gpt-image-2` provider support behind `AFM_IMAGE_PROVIDER=openai`, including Images API generation/editing and Responses API vision review configuration.
- Added `academic-figures://provider-capabilities` so MCP hosts can discover provider support for generation, editing, review, multi-turn editing, and structured render options.

### Changed in 0.4.5

- Forwarded `output_size` as a structured provider hint from generation, replay, and journal-retarget flows so OpenAI Images API calls can receive a concrete `size` parameter.
- Updated VS Code connection settings, env templates, README guidance, and provider discovery metadata for OpenAI and Ollama profiles.

### Fixed in 0.4.5

- Fixed publication-image output contracts so unsupported output suffixes are rejected and explicit `output_format` requests produce matching canonical suffixes.
- Fixed publication-image validation so directories and unreadable rasters return domain validation errors instead of raw filesystem/Pillow exceptions.
- Fixed metadata-only DPI warnings so they report the requested target DPI instead of always saying 600 DPI.
- Fixed provider configuration safety by rejecting unknown `AFM_IMAGE_PROVIDER` values instead of silently falling back to Google.

## [0.4.4]

### Fixed in 0.4.4

- Fixed release workflow drift by applying Ruff formatting to the remaining Python files that caused the `Quality Gate` job in `publish.yml` to fail before packaging and Marketplace publication.

## [0.4.3]

### Added in 0.4.3

- Added Copilot research workflow hooks, shared pipeline policy files, reusable research agents, and PubMed/Zotero skill documents for guided literature workflows.
- Added direct planning and generation support for non-PMID briefs such as preprints, repositories, and freeform research concepts through `source_title`, `source_kind`, `source_summary`, and `source_identifier` inputs.
- Added `get_manifest_detail` and `record_host_review` so hosts can inspect full lineage-aware review history and persist external visual-review verdicts back into manifests.

### Changed in 0.4.3

- `generate_figure` is now the default single-entry drawing surface and performs internal plan-first orchestration when callers start from a PMID or generic source brief.
- Output delivery now accepts `output_format` and performs internal raster conversion for `png`, `gif`, `jpeg`, and `webp`, while keeping `svg` as pass-through only.
- Provider-side automated review is now persisted across generation, replay, and journal-retarget flows under the `provider_vision_required_host_optional` manifest policy.
- Updated the VS Code extension branding with a marketplace gallery banner and a regenerated transparent icon asset that removes the visible white border.

### Fixed in 0.4.3

- Fixed composite-render manifest output paths so persisted manifest records follow the final converted asset path.
- Fixed release-ready format coverage by adding official GIF validation, conversion, documentation, and regression coverage.

## [0.4.2]

### Changed in 0.4.2

- The VS Code extension local-source runtime now launches the dev MCP server through `src.server`, which keeps one canonical FastMCP instance alive during stdio startup.
- The extension-generated `.vscode/mcp.json` now migrates legacy `academicFigures` entries into the canonical `academic-figures` server entry while preserving existing `envFile` or `env` settings.

### Fixed in 0.4.2

- Fixed local dev MCP sessions in VS Code so `ListToolsRequest` no longer returns zero tools when the workspace source tree is launched through `uv run ... python -m ...`.
- Fixed workspace MCP bootstrap drift by rewriting legacy `src.presentation.server` launch targets to the `src.server` shim used by the canonical server module.

## [0.4.1]

### Added in 0.4.1

- Added `scripts/package_smoke.py` plus a GitHub Actions package-smoke matrix that validates the `uvx --from . afm-run` install path on Ubuntu, macOS, and Windows.
- Added bundled knowledge markdown assets inside the VS Code extension so packaged installs can open built-in guides without requiring the repository checkout.
- Added VS Code one-click MCP install links and `uvx` package-mode examples to the main README, following the Zotero Keeper onboarding pattern.

### Changed in 0.4.1

- Academic Figures sidebar title actions now expose Setup Wizard, Configure Connection, Browse Knowledge Assets, and a welcome hint for first-use credential setup.
- Knowledge-asset browsing now resolves workspace files first and falls back to bundled extension resources for packaged VSIX installs.
- Cross-platform docs now recommend `uvx --from academic-figures-mcp afm-server` as the primary install path for macOS, Linux, and Windows users.

### Fixed in 0.4.1

- Fixed the published VS Code extension manifest by declaring `mcpServerDefinitionProviders`, which unblocks activation in the extension host.
- Fixed packaged VSIX installs so bundled markdown knowledge assets open correctly instead of incorrectly resolving only against the active workspace.

## [0.4.0]

### Added in 0.4.0

- Added exact-label planning support through `expected_labels`, so text-heavy figures can carry explicit label targets into prompt construction and downstream verification.
- Added a CJK-aware prompt block that explicitly instructs exact text fidelity, anti-romanization behavior, and label preservation for zh-TW / zh-CN / ja-JP / ko-KR outputs.
- Added a standalone `verify_figure` MCP tool for post-hoc figure QA with label verification and domain-scored quality review.
- Added a `multi_turn_edit` MCP tool that keeps iterative edit sessions open across multiple instructions for corrective refinement.
- Added `src/application/verify_figure.py` and `src/application/multi_turn_edit.py` use cases to expose verification and multi-turn edit workflows cleanly through the application layer.
- Added `GeminiImageVerifier` for image self-review with score parsing, label checks, and structured quality verdicts.
- Added targeted CJK / quality-gate regression coverage in `tests/unit/application/test_cjk_quality_gate.py`.

### Changed in 0.4.0

- Planner routing now escalates text-heavy CJK requests toward SVG/code-render paths earlier instead of treating them like ordinary bitmap generation.
- Model resolution now understands abstract intents such as `high_fidelity` and can escalate CJK-sensitive requests to a stronger image model automatically.
- `generate_figure` now runs an optional post-generation quality gate and returns structured verification metadata when a verifier is available.
- README and MCP surface descriptions now reflect the expanded verification, exact-label, and iterative editing capabilities.

### Fixed in 0.4.0

- Fixed Ollama provider config precedence so `OLLAMA_MODEL` is honored even when a generic `GEMINI_MODEL` is present in the environment.
- Restored a green full release gate across Ruff, mypy, Bandit, and the full pytest suite.

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
