# System Patterns

## Architectural Patterns

- Pattern 1: Keep literature retrieval behind a narrow MetadataFetcher boundary.

  The figure-generation pipeline should depend only on the minimal paper context it needs, such as PMID, title, abstract, journal, and related metadata. Rich discovery capabilities should remain outside the core figure workflow unless they are injected through a dedicated adapter.
- Pattern 2: Treat academic search as an upstream MCP or sidecar service, not as an internal subsystem of the figure runtime.

  If the product later needs unified search, PICO, citation graphs, or full-text enrichment, prefer integrating a dedicated research-search MCP and translating its output into domain Paper objects rather than porting that stack into this repository.
- Pattern 3: No compatibility layer without an active consumer.

  This repository is greenfield. Do not add or preserve wrapper modules, alternate package names, or duplicate entrypoints unless a real in-repo consumer requires them.
- Pattern 4: Expose only one public image-creation contract.

  The MCP surface should converge on one generic generation tool for new visual assets. Planner, evaluator, preset-resolution, batch, and workflow-state tools should act as harness layers that prepare or validate requests for that renderer instead of becoming parallel creation APIs.

## Design Patterns

- Pattern 1: Anti-corruption adapter for external research systems.

  External search services may expose richer schemas than this repo needs. Use a thin infrastructure adapter to map those payloads into the domain Paper model so application-layer use cases remain stable.

## Common Idioms

- Idiom 1: Keep figure workflow inputs small and typed at the boundary.

  The presentation and application layers should receive normalized PMIDs, figure types, route hints, and metadata snapshots, not entire search-engine response payloads.
- Idiom 2: Import canonical modules directly.

  Use `src.presentation.server`, `src.presentation.direct_run`, `src.infrastructure.*`, and other actual layer modules directly instead of adding convenience re-export files at the package root.
- Idiom 3: Pass a planned payload into the renderer, not raw domain intake.

  PMID, journal intent, rubric gates, and style discovery belong to harness logic. The final generation boundary should receive a generic render-ready payload so the same renderer can be reused for figures, icons, and other visual assets.


## YAML Journal Registry Injection

Journal figure requirements are stored as machine-readable YAML profiles and resolved from explicit target_journal input or source journal metadata. PromptEngine appends the matched profile constraints to prompts so planning and generation stay data-driven.

### Examples

- templates/journal-profiles.yaml
- src/infrastructure/journal_registry.py
- src/infrastructure/prompt_engine.py
- src/application/plan_figure.py
- src/application/generate_figure.py


## Thin presentation handlers with use-case delegation

MCP tools should validate/normalize input and then delegate orchestration to application use cases. Presentation code should not construct or control infrastructure implementations directly; cross-layer behavior should flow through domain interfaces and the dependency container.

### Examples

- src/presentation/tools.py
- src/application/composite_figure.py
- src/presentation/dependencies.py


## Detect bitmap media type from content, not extension

External image providers may return JPEG bytes even when older flows or callers assume a `.png` filename. Normalize media type from magic bytes at the infrastructure boundary and derive output paths from the resulting `GenerationResult.file_extension` so saved files always match their real encoding.

### Examples

- src/infrastructure/gemini_adapter.py
- src/application/edit_figure.py
- src/domain/entities.py


## Keep metadata retrieval pluggable behind MetadataFetcher

The application layer should continue to depend on a narrow `MetadataFetcher` interface that returns only normalized `Paper` metadata. Infrastructure can then swap between direct PubMed E-utilities, file-backed demo corpora, or later sidecar/MCP adapters without changing plan/generate use cases.

### Examples

- src/domain/interfaces.py
- src/infrastructure/pubmed_client.py
- src/infrastructure/file_metadata_fetcher.py
- src/presentation/dependencies.py
