# Progress (Updated: 2026-04-12)

## Done

- Added templates/journal-profiles.yaml as the machine-readable journal registry.
- Implemented infrastructure journal registry loading and PromptEngine journal requirement injection.
- Extended plan_figure and generate_figure to accept target_journal and automatically apply journal constraints.
- Added tests for prompt-engine journal resolution, plan payload propagation, and generation prompt injection.
- Validated changes with Ruff and pytest (14 passed).
- Recorded the next six requested product capabilities in Memory Bank for future planning and implementation.
- Added root ROADMAP.md to formalize capability sequencing and delivery themes.
- Added root CHANGELOG.md to track notable repo changes in a durable project document.
- Updated README.md to expose roadmap, changelog, and other key project documents.
- Added a cross-platform local launcher and replaced PowerShell-only static MCP startup guidance with shell-neutral `uv --project` launch instructions.
- Converged the legacy PMID input path in generate_figure onto an internal plan-first bridge so generation always runs from planned_payload.
- Synced the VS Code extension vector icon with the newer PNG brand asset.
- Generated repo-owned README visuals through the local MCP workflow and saved curated payloads, output images, and QA reports under .academic-figures/.
- Iterated the workflow figure to a stricter v2 so the duplicated Payload step was removed and the main flow is now unambiguous.
- Updated README.md to embed the generated visuals, link their QA reports, and explicitly document that both the images and reviews are self-generated through this repository.
- Recovered the post-merge PR #2 CI regressions by fixing composite typing, root-level Ruff violations, prompt-loader exception handling, and PubMed HTTP fetching.
- Added isolated unit coverage for PubMed metadata parsing and failure wrapping.
- Validated the repaired branch with Ruff, Ruff format, mypy, Bandit, and pytest (30 passed).

## Doing

- Maintaining the current generic renderer plus journal-registry baseline while prioritizing the next roadmap capabilities around posters, grouped figures, composites, prompt retention, and style reuse.

## Next

- Support poster generation as a first-class output mode.
- Support grouped multi-panel figure generation.
- Support montage/composite assembly, such as turning four images into one larger figure.
- Support retargeting one existing image to different journal requirements without rebuilding the concept from scratch.
- Persist prompts and prompt packs so assets can be reproduced later.
- Extract reusable style prompts from an existing image so the style can be applied again.
