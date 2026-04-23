# Progress (Updated: 2026-04-23)

## Done

- 確認 0.4.4 release gate 全數通過：ruff check、ruff format --check、mypy、bandit、pytest
- 完成 Python 套件建置與 VS Code extension VSIX 打包驗證
- 已建立並推送 0.4.4 release commit 到 main
- 已建立並推送 annotated tag v0.4.4
- 確認 GitHub Actions 的 Publish workflow 已因 v0.4.4 tag 觸發並成功完成
- 已完成架構清理第一步：收斂 render route 契約，planner 只輸出可執行 route，generator 對 unsupported route 明確報錯
- render route 契約相關單元測試通過（49 passed），窄範圍 Ruff 檢查通過
- 已完成第二步：新增 FigureEvaluator port，讓 EvaluateFigureUseCase 不再依賴 ImageGenerator.edit
- 已完成第三步：GenerateFigureUseCase 支援注入 planner，移除 composition root 之外的直接 use case 建構依賴
- evaluation 與 plan-first bridge 相關窄範圍測試、Ruff 檢查皆已通過
- 已開始拆解 provider adapter：GeminiAdapter 退為 façade，generation、edit、fallback 已移到獨立類別責任
- 已補上 container 初始化鎖：singleton 與 lazy dependency 初始化現在都有 lock 保護，降低 streamable-http 並發 race
- provider/container 相關窄範圍驗證通過：34 個回歸測試與 Ruff 檢查皆通過
- 已修正 mac 新機器 package/local process 啟動脆弱性：extension 會解析安全 cwd，Python console script 也會在 import 前修復 invalid cwd
- 啟動穩定性修正已驗證：bootstrap 測試通過、afm-run package entrypoint 可正常啟動、extension TypeScript 編譯通過
- 已把 generation/edit/evaluate 的 Google/OpenRouter/Ollama provider-specific 路徑抽到獨立 runtime module，gemini_adapter.py 不再自己持有這些分支實作
- 已開始型別化 adapter 內部契約：新增 typed ProviderFailure / RuntimeOutcome，fallback 與 runtime 邊界不再靠自由字串協調
- provider runtime 重構已驗證：generate/edit/evaluate/adapter 聚焦回歸 29 個測試通過，新增 OpenRouter typed failure 測試通過，Ruff 檢查通過
- 已用兩個 subagent 審查 safe cwd 啟動修正，並補強啟動鏈缺口：local direct-run 現在也走 bootstrap shim，不再繞過 cwd 修復
- 已補強 mcpProvider 啟動整合：local source 探測改與真實 entrypoint 對齊，server runtime 解析失敗時會回報明確錯誤，workspace env file 會忽略高風險 loader/Python 路徑變數
- 已補齊 bootstrap 測試缺口：驗證 PWD 副作用、AFM_SAFE_CWD 優先順序與 dedupe、server/direct-run lazy delegation
- 已修正 package-mode wheel 資產缺漏：templates 與 journal-profiles.yaml 現在隨 wheel 一起封裝，並已在 repo 外用 built wheel 成功執行 afm-run plan
- 已把 GeminiImageVerifier 改成共用 provider runtime / typed failure 邊界，不再自己分支 Google/OpenRouter provider parsing
- 已為公開 GenerationResult 新增 typed status/error contract：加入 GenerationResultStatus、GenerationErrorKind，並保留既有 ok/error 相容層
- 已把 generate/edit/evaluate/replay/retarget 的 application response 補上 result_status / error_kind 序列化欄位，開始把 typed contract 往 public response 往上帶
- verifier/runtime/result contract 相關最終驗證通過：73 個聚焦回歸測試與 Ruff 檢查皆通過
- 已把 review_harness / verify_figure / multi_turn_edit 收斂到同一套 typed review/result contract：review_route、review_status、route_status 與 final_result_status 等欄位已統一序列化
- review contract 第二階段驗證通過：generate/replay/retarget/host-review 整合回歸與新增 review_harness、multi_turn_edit、verify_figure 測試共 25 個通過，Ruff 檢查通過
- 已把 manifest list/detail 的 host-facing schema 收斂到同一套 public serializer：quality_gate、review_summary、review_history、review_timeline 現在都會補齊 typed route/review 欄位，不再直接透傳 raw persisted dict
- 已更新 presentation inventory resource，明確對 host/extension 說明 manifest 與 review_contract 的 typed 欄位；確認 extension 目前沒有直接消費這些 manifest/review schema，因此這輪不需修改 extension 程式碼
- manifest/detail/presentation schema 相關最終驗證通過：24 個聚焦回歸測試與 Ruff 檢查皆通過
- 已補齊剩餘單點 tool response 的共用 review public serializer：record_host_review、generate_figure、replay_manifest、retarget_journal 現在都不再直接回傳 raw quality_gate/review_summary/review_history
- 已消除 persisted/public review metadata 漂移：build_review_summary 的 host fallback route 與 provider/host review history entry 現在都會產出完整的 legacy+typed 欄位，讓 stored data 與 public serializer 一致
- 已在 inventory resource 補上 extension future-consumer 指引：若 extension 開始直接消費 manifest/detail payload，應將 typed review contract 映射到 TypeScript 介面，而不是零散讀 raw nested keys
- review public serializer 第三階段驗證通過：24 個聚焦回歸測試與 Ruff 檢查皆通過
- 已新增 dedicated error serializer：presentation exception payload 與主要 host-facing application failure response 現在統一輸出 error_status / error_category / error
- 已把 error contract 接到 presentation `_error_payload()`、generate/edit/evaluate/replay/retarget 等失敗回傳，保留既有 status/error 與 result_status/error_kind 相容欄位
- 已在 inventory resource 補上 error_contract 與 extension future TypeScript mapping guidance，先固定 host-facing schema，再等 extension 真正消費 payload 時做 1:1 TS 介面映射
- typed error contract 驗證通過：45 個聚焦回歸測試與 Ruff 檢查皆通過
- 已把剩餘 aggregate response 收斂到 dedicated typed summary contract：batch_generate 與 list_manifests 現在都會輸出 aggregate_kind / aggregate_status / item_count，batch_generate 另外保留 total_count / success_count / failed_count
- 已在 inventory resource 補上 aggregate_contract，並明確記錄 extension 仍應等到真正直接消費 aggregate/manifest payload 時，再與 review/error schema 一起做 1:1 TypeScript 介面映射
- aggregate contract 驗證通過：batch_generate、manifest_workflows、presentation resources 聚焦回歸 12 個測試通過，Ruff 檢查通過
- 已完成雙獨立 agent code review 後的整合修正：manifest `target_journal=None` round-trip、retarget warning 持久化順序、multi-turn 空/零回合驗證、package-mode templates/journal profiles、VS Code stdio transport 一致性、journal YAML date JSON safety 等問題已修正
- 已新增純 code publication image preparation 工具：`prepare_publication_image` MCP tool 與 `afm-run prepare-image` CLI 可用 Pillow 將既有 raster 圖片依最終印刷尺寸重採樣並寫入 600 DPI metadata，不會呼叫任何生成 provider
- 已補齊 publication image processor 的 application / infrastructure / presentation 測試，並更新 README 與 inventory tool list
- 最新全量驗證通過：`uv run pytest` 181 passed、`uv run ruff check .`、`uv run mypy src tests`，並實跑 `afm-run prepare-image` 成功輸出 600 DPI TIFF
- 已完成 0.4.5 發布前功能修正：publication image processor 會拒絕 unsupported output suffix、修正 output_format/副檔名不一致、包裝目錄/不可讀影像錯誤、並讓 metadata-only warning 顯示實際 target DPI
- 已新增 OpenAI `gpt-image-2` provider path：`AFM_IMAGE_PROVIDER=openai` 使用 Images API 進行 generation/edit，Responses API + `OPENAI_VISION_MODEL` 進行 provider-side review
- 已把 `output_size` 從 generate/replay/retarget application 層結構化傳到 provider runtime，OpenAI Images API 會優先使用該值作為 `size`
- 已新增 `academic-figures://provider-capabilities` resource，公開 google/openrouter/openai/ollama 的 generate/edit/verify/multi-turn/mask/structured option capability matrix
- 已修正 provider config safety：未知 `AFM_IMAGE_PROVIDER` 現在 fail closed，不再靜默 fallback 到 Google
- 已更新 VS Code extension 設定與 setup/env template 路徑，支援 OpenAI SecretStorage/env-file/process-env profile
- 0.4.5 release gate 已通過：`uv run pytest` 195 passed、`uv run ruff check .`、`uv run mypy src tests`、VS Code extension lint/compile、`uv run python scripts/package_smoke.py`、`afm-run prepare-image` suffix rewrite smoke

## Doing

- 準備 0.4.5 release：版本/CHANGELOG/Memory Bank 與 full validation 已完成，接著分段 commit、annotated tag、push

## Next

- 建立 0.4.5 release commit、annotated tag，並 push main + tag
