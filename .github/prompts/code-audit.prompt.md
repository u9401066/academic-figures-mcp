---
description: "深度程式碼審計 — 5 維度全面掃描"
mode: "agent"
tools: ['codebase', 'editFiles', 'fetch', 'findTestFiles', 'problems', 'runCommands', 'search', 'usages']
---

# 深度程式碼審計

請對以下範圍執行 5 維度深度審計：

## 審計範圍
- **目標**: `src/` 目錄
- **架構**: DDD (Domain → Application → Infrastructure → Presentation)
- **語言**: Python 3.10+
- **框架**: FastMCP, google-genai

## 審計維度

### 1. 程式碼品質 (Code Quality)
- 執行 `uv run ruff check .` 掃描
- 檢查命名一致性、程式碼複雜度
- 識別重複程式碼

### 2. 安全性 (Security)
- 執行 `uv run bandit -r src/`
- OWASP Top 10 手動檢查
- Secrets/credentials 偵測

### 3. 架構合規 (Architecture Compliance)
- DDD 分層是否正確
- 依賴方向: `Presentation → Application → Domain ← Infrastructure`
- Domain 層是否有外部 import

### 4. 測試覆蓋 (Test Coverage)
- 執行 `uv run pytest --cov=src --cov-report=term-missing`
- 關鍵路徑是否有測試
- 邊界條件覆蓋

### 5. 文檔同步 (Documentation Sync)
- README 是否反映最新架構
- Memory Bank 是否最新
- copilot-instructions.md 是否一致

## 輸出格式

```
## 🔬 審計報告

### 評分總覽
| 維度 | 分數 | 狀態 |
|------|------|------|
| 品質 | X/10 | 🟢/🟡/🔴 |
| 安全 | X/10 | 🟢/🟡/🔴 |
| 架構 | X/10 | 🟢/🟡/🔴 |
| 測試 | X/10 | 🟢/🟡/🔴 |
| 文檔 | X/10 | 🟢/🟡/🔴 |

### 問題清單 (按嚴重度排序)
...

### 行動計畫
...
```
