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


## Output formatting via domain service

需要 output format normalization、media type mapping 或 raster conversion 的 use case，不直接依賴 Pillow 或檔案系統，而是依賴 domain OutputFormatter 介面，由 infrastructure 實作並在 presentation/dependencies.py 注入。

### Examples

- src/domain/interfaces.py
- src/infrastructure/output_formatter.py
- src/application/generate_figure.py
- src/application/edit_figure.py
- src/presentation/dependencies.py


## Dual-route review harness

生成後的 review contract 同時承認 provider_vision 與 host_vision 兩條路。provider_vision 由 application/review_harness.py 統一執行自動 quality gate，結果與 review_summary 會持久化到 GenerationManifest；host_vision 視為外部可用路徑，由 Copilot/宿主根據回傳的 review_summary 決定是否補做看圖審查。acceptance policy 為 provider_vision_required_host_optional。

### Examples

- src/application/review_harness.py
- src/application/generate_figure.py
- src/application/replay_manifest.py
- src/application/retarget_journal.py
- src/application/list_manifests.py
- src/domain/entities.py


## Host review write-back

當宿主模型或 Copilot 直接看圖完成外部 review 時，不直接改 generate flow，而是呼叫 record_host_review 把 passed/summary/issues 寫回既有 manifest.review_summary。review_harness 會重新計算 passes_recorded 與 requirement_met，但 host_vision 不會覆蓋 failed 或 missing 的 provider baseline。

### Examples

- src/application/record_host_review.py
- src/presentation/tools.py
- src/application/review_harness.py
- src/application/list_manifests.py


## Manifest detail with lineage review timeline

對外的 manifest surface 分成 summary 與 detail 兩層：list_manifests 只提供摘要；get_manifest_detail 會載入單一 manifest，必要時沿 parent_manifest_id 回溯 lineage，並回傳完整 manifest、各代 lineage entry 與 flattened review_timeline。review_history 是 manifest 的一級持久化欄位，provider_vision 與 host_vision 事件都寫在這裡。

### Examples

- src/application/get_manifest_detail.py
- src/application/list_manifests.py
- src/application/generate_figure.py
- src/application/record_host_review.py
- src/domain/entities.py


## Provider baseline review gate

review_summary 的 requirement_met 不再代表任一路徑通過即可，而是明確依賴 provider_baseline_met。provider_vision 必跑且必須 passed；host_vision 即使 passed，也只會增加 passes_recorded 與歷史事件，不會把 failed/missing provider baseline 轉成通過。

### Examples

- src/application/review_harness.py
- src/application/record_host_review.py
- tests/unit/application/test_manifest_workflows.py
- tests/unit/application/test_generate_figure.py


## Provider capability discovery

Provider differences are exposed through `academic-figures://provider-capabilities` instead of hidden in host logic. Hosts should inspect generate/edit/verify/multi-turn/mask and structured option support before assuming a provider can perform a route.

### Examples

- src/presentation/resources.py
- src/infrastructure/config.py
- src/infrastructure/gemini_provider_runtimes.py


## Structured provider render hints

Generation should pass render options such as `output_size` through the ImageGenerator/runtime boundary, not only embed them in prompt text. Providers that support structured size parameters, such as OpenAI Images API, can use the hint directly; providers that do not can safely ignore it.

### Examples

- src/domain/interfaces.py
- src/application/generate_figure.py
- src/application/replay_manifest.py
- src/application/retarget_journal.py
- src/infrastructure/gemini_adapter.py
