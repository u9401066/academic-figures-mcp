# Active Context

## Current Goals

- The YAML-backed journal requirement registry and automatic prompt injection flow are in place for Nature, Science, JAMA, NEJM, and Lancet.
- The requested next capabilities are now captured both in Memory Bank and in repo-level product documents.
- Cross-platform MCP launch hardening is in progress so the repo-level configuration and manual bootstrap path work cleanly on Windows, macOS, and Linux.
- The current implementation pass is converging legacy PMID generation onto a strict internal plan-first flow while keeping the external compatibility bridge alive.
- The VS Code extension branding assets are being synchronized so icon.svg stays consistent with the new PNG icon.
- The repository is now using its own MCP generate/evaluate workflow to create README-facing introduction, architecture, and workflow visuals, with the workflow diagram iterated to a stricter v2.
- Current planning focus is to prioritize implementation for poster generation, grouped figures, composite montage output, journal retargeting for an existing image, prompt retention for replay, and style-to-prompt extraction.
- Current delivery focus is CI recovery after PR #2 merge: clear Ruff, mypy, and Bandit failures, verify manifest/composite flows still behave correctly, and re-run the existing validation suite to green.

## Current Blockers

- Local validation requires bootstrapping `uv` in the sandbox before the standard repo checks can run.
