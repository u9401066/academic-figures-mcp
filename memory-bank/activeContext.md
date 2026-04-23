# Active Context

## Current Goals

- Execute the architecture cleanup incrementally instead of a big-bang rewrite.
- Preserve the startup hardening for package/local-process launch: invalid cwd should no longer crash before the server imports.
- Preserve the new launch rule: all local entrypoints, including direct-run, must go through bootstrap before importing presentation modules.
- Preserve the completed slices: executable render-route contract, dedicated FigureEvaluator port, and injected planner for plan-first generation.
- Preserve the new adapter split: GeminiAdapter is now a façade over generation/edit adapters, with fallback isolated from the façade itself.
- Preserve the new runtime split: generation, edit, and evaluation now delegate to provider runtime modules with typed ProviderFailure / RuntimeOutcome boundaries.
- Preserve the new verifier split: GeminiImageVerifier now reuses the same typed provider runtime path instead of owning provider-specific response parsing.
- Preserve the new packaging rule: templates/journal assets must ship inside wheel artifacts so uvx/package mode does not depend on repo-root files.
- Preserve the new result contract: GenerationResult now carries typed status/error_kind, and major application responses serialize result_status/error_kind while keeping legacy status/error compatibility.
- Preserve the new review contract: review_harness, verify_figure, and multi_turn_edit now serialize typed review/result metadata such as review_route, review_status, route_status, and final_result_status while preserving legacy compatibility fields.
- Preserve the new manifest serializer: list_manifests and get_manifest_detail now normalize persisted review_summary/review_history/quality_gate into typed host-facing fields before returning them.
- Note: the VS Code extension currently has no direct consumer of manifest/review payload fields, so host-facing schema convergence in this slice landed in application/presentation resources rather than extension runtime code.
- Preserve the new review public serializer: record_host_review, generate_figure, replay_manifest, and retarget_journal now all emit review metadata through the same serializer instead of hand-assembling raw response dicts.
- Preserve the persisted/public parity fix: default host review routes and persisted review history entries now carry complete compatibility fields so normalized public output does not drift from freshly saved manifests.
- Preserve the new error public serializer: presentation exception payloads and major host-facing failure responses now emit error_status/error_category through one shared contract while keeping legacy status/error fields.
- Preserve the extension timing rule: do not add unused TS runtime interfaces yet; once the extension becomes a direct consumer of manifest/detail payloads, map the stabilized review/error contract 1:1 into TypeScript interfaces in that same slice.
- Preserve the new aggregate contract: batch_generate and list_manifests now emit aggregate_kind/aggregate_status/item_count through one shared serializer, with batch_generate additionally exposing total_count/success_count/failed_count.
- Preserve the extension timing rule for aggregate payloads too: do not add unused TS runtime interfaces yet; once the extension becomes a direct consumer of manifest/detail or aggregate payloads, map the stabilized review/error/aggregate contract 1:1 into TypeScript interfaces in that same slice.
- Preserve the new code-only publication image preparation route: `prepare_publication_image` / `afm-run prepare-image` use Pillow only, never image-generation providers, and report `processing_route=code_only_pillow` plus `generation_used=false`.
- Preserve the DPI semantics: true 600 DPI preparation requires final print size (`width_mm` and/or `height_mm`); without print size the tool writes DPI metadata only and warns rather than claiming extra detail.
- Preserve the publication-image delivery hardening: unsupported output suffixes are rejected, explicit `output_format` requests produce matching canonical suffixes, directories/unreadable rasters become domain validation errors, and metadata-only warnings report the requested target DPI.
- Preserve the OpenAI-ready provider path: `AFM_IMAGE_PROVIDER=openai` selects `gpt-image-2` for Images API generation/editing, uses `OPENAI_VISION_MODEL` for Responses API review, and receives `output_size` as a structured provider hint instead of only prompt text.
- Preserve provider fail-closed behavior: unknown `AFM_IMAGE_PROVIDER` values now raise configuration errors instead of silently falling back to Google.
- Prepare the 0.4.5 release slice: keep version, changelog, memory bank, tag, and PyPI/VS Code release artifacts aligned.

## Current Blockers

- No current blocker. Remaining risk before release is final full-suite/package smoke validation and successful tag push.
