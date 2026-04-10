# Academic Figures MCP — Copilot Instructions

此文件為 VS Code GitHub Copilot 及 Claude Code 提供專案上下文與操作規範。

## Project Overview
Academic Figures MCP is a **Model Context Protocol server** that turns PubMed papers
into publication-ready scientific figures using Google Gemini image generation.

整合了：
- DDD (Domain-Driven Design) 四層架構
- Memory Bank 專案記憶系統
- 14 個 Custom Copilot Agents（含模型成本策略）
- 完整 Pre-commit Hooks（16+ hooks）

## 開發哲學 💡

> 「想要寫文件的時候，就更新 Memory Bank 吧！」
> 「想要零散測試的時候，就寫測試檔案進 tests/ 資料夾吧！」

- 不要另開檔案寫筆記，直接寫進 Memory Bank
- 今天的零散測試，就是明天的回歸測試

## Architecture: Domain-Driven Design (DDD)

```
src/
  domain/          ← Pure business logic, NO external imports
  application/     ← Use-case orchestration
  infrastructure/  ← External integrations (Gemini, PubMed, file I/O)
  presentation/    ← MCP server surface (tools, resources, prompts)
```

### Layer Rules (STRICTLY ENFORCED)
| Layer | May import from | Forbidden imports |
|-------|----------------|-------------------|
| `domain/` | stdlib, dataclasses, enum, typing, abc | Any external package |
| `application/` | `domain/` | Infrastructure classes directly |
| `infrastructure/` | `domain/` (interfaces, entities) | `application/`, `presentation/` |
| `presentation/` | `application/`, `infrastructure/` (for DI), `domain/` | N/A |

依賴方向：`Presentation → Application → Domain ← Infrastructure`

### Key Patterns
- **Dependency Injection**: `presentation/dependencies.py` wires infrastructure into use cases.
- **Domain interfaces**: `domain/interfaces.py` defines ABCs; infrastructure implements them.
- **Value Objects**: Immutable, use `@dataclass(frozen=True)` or `Enum`.
- **Use Cases**: One class per business operation, single `execute()` method.
- **Repository Pattern**: DAL (Data Access Layer) 必須獨立。

## Technology Stack
- **Runtime**: Python 3.10+
- **MCP**: `mcp[cli]>=1.27.0` (FastMCP)
- **AI**: `google-genai` (Gemini image generation)
- **Package manager**: `uv` (never pip/conda)
- **Lint**: `ruff`
- **Types**: `mypy --strict`
- **Tests**: `pytest`
- **Security**: `bandit`
- **Pre-commit**: ruff, mypy, pytest, bandit, gitleaks, conventional-commits, commit-size-guard

## Python 環境（uv 優先）

- 優先使用 uv 管理套件和虛擬環境
- 禁止全域安裝套件

```bash
# 初始化環境
uv venv
uv sync --all-extras

# 安裝依賴
uv add package-name
uv add --dev pytest ruff mypy bandit
```

## Conventions
- **Language**: All code comments and docstrings in **English**.
  User-facing prompts and MCP tool descriptions may use **Traditional Chinese (zh-TW)**.
- **Imports**: Always use absolute imports from `src.*`.
- **Type hints**: Required on all public functions.
- **Error handling**: Domain exceptions in `domain/exceptions.py`.
  Presentation layer catches and returns structured error dicts.
- **Tests**: Mirror source structure under `tests/unit/`.

## Memory Bank 同步

每次重要操作必須更新 Memory Bank：

| 時機 | 更新檔案 |
|------|----------|
| 完成任務 | progress.md (Done) |
| 開始任務 | progress.md (Doing), activeContext.md |
| 重大決策 | decisionLog.md |
| 架構變更 | architect.md, systemPatterns.md |

## Git 工作流

提交前必須執行檢查清單：

1. ✅ Memory Bank 同步（必要）
2. 📖 README 更新（如需要）
3. 📋 CHANGELOG 更新（如需要）
4. 遵循 Conventional Commits 格式

### Pre-commit Hooks

```bash
# 安裝 hooks
uv add --dev pre-commit
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```

| Hook | 用途 |
|------|------|
| ruff (lint+format) | Python 程式碼品質 |
| mypy | 型別檢查 |
| bandit | 安全掃描 |
| gitleaks | Secrets 偵測 |
| conventional-pre-commit | Commit message 格式 |
| commit-size-guard | 限制每次 commit ≤ 30 檔案 |
| memory-bank-reminder | 提醒同步 Memory Bank |
| agent-freshness-check | 檢查 Agent 模型/工具是否過時 |

## Commands
```bash
uv sync                 # Install all deps
uv run pytest           # Run tests
uv run ruff check .     # Lint
uv run ruff format .    # Format
uv run mypy src/        # Type check
uv run bandit -r src/   # Security scan
uv run pre-commit run --all-files  # All hooks
```

## MCP Server Entry Point
```bash
uv run python -m src.presentation.server   # stdio transport
MCP_TRANSPORT=streamable-http uv run python -m src.presentation.server
```

## File Naming
- Domain entities: noun (`entities.py`, `paper.py`)
- Use cases: verb phrase (`generate_figure.py`, `edit_figure.py`)
- Infrastructure: role suffix (`gemini_adapter.py`, `pubmed_client.py`)
- Presentation: MCP concept (`tools.py`, `resources.py`, `prompts.py`)

## 🤖 Copilot Agents

位於 `.github/agents/`：

| Agent | 職責 | 推薦模型 |
|-------|------|----------|
| architect | 系統架構設計 + Memory Bank | Claude Sonnet 4.6 → GPT-5.4 |
| code | 實作功能 + 程式碼編寫 | Claude Sonnet 4.6 → GPT-5.4 |
| ask | 專案問答 + 知識查詢 | GPT-4.1 → Claude Haiku 4.5 |
| debug | 除錯分析 + 問題修復 | Claude Sonnet 4.6 → GPT-5.4 |
| audit | 深度程式碼審計（5 維度） | Claude Opus 4.6 → Claude Sonnet 4.6 |
| orchestrator | 總指揮 — 拆解需求、委派、追蹤 | Claude Opus 4.6 → GPT-5.4 |
| deep-thinker | 深度推理 — 算法、根因、架構權衡 | Claude Opus 4.6 → GPT-5.4 |
| researcher | 只讀探索 — codebase 調查、依賴分析 | Gemini 3.1 Pro → Claude Sonnet 4.6 |
| test-runner 🆓 | 跑測試 + 迭代修復 | GPT-5 mini → GPT-4.1 |
| context-loader 🆓 | 讀取 Memory Bank + codebase 摘要 | GPT-4.1 → GPT-5 mini |
| review-panel | 多模型審查委員會（3 AI 交叉審查） | Claude Opus 4.6 |
| reviewer-anthropic | Claude 審查 — 安全性、型別 | Claude Sonnet 4.6 |
| reviewer-openai | GPT 審查 — 效能、可讀性 | GPT-5.4 |
| reviewer-google | Gemini 審查 — 架構、測試 | Gemini 3.1 Pro |

> 🆓 = Free model agents for high-volume, repetitive tasks

## 📎 Copilot Prompts（可重複使用）

位於 `.github/prompts/`：

| Prompt | 用途 |
|--------|------|
| generate-figure.prompt.md | PMID → 學術圖表生成 |
| edit-figure.prompt.md | 自然語言修改圖表 |
| evaluate-figure.prompt.md | 8 維度品質評估 |
| code-audit.prompt.md | 深度程式碼審計 |
| security-scan.prompt.md | 安全掃描 |

## 💸 Memory Checkpoint 規則

為避免對話被 Summarize 壓縮時遺失重要上下文：

### 主動觸發時機
1. 對話超過 10 輪
2. 累積修改超過 5 個檔案
3. 完成一個重要功能/修復
4. 使用者說要離開/等等

### 必須記錄
- 當前工作焦點
- 變更的檔案列表（完整路徑）
- 待解決事項
- 下一步計畫

## 回應風格
- 使用繁體中文
- 提供清晰的步驟說明
- 執行操作後更新 Memory Bank
- 遵循 Conventional Commits 格式
- 程式碼是文檔的「編譯產物」

## 常用指令

```
「準備 commit」       → 執行完整提交流程
「快速 commit」       → 只同步 Memory Bank
「建立新功能 X」      → 生成 DDD 結構
「review 程式碼」     → 程式碼審查
「更新 memory bank」  → 同步專案記憶
「checkpoint」        → 記憶檢查點
「審計」              → 深度程式碼審計
```
