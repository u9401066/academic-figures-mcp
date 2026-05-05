# 子法：Git 工作流規範

> 父法：CONSTITUTION.md 第三章

## 第 1 條：提交前檢查清單

依序執行以下步驟（可透過 `--skip-X` 跳過）：

| 順序 | 項目 | Skill | 可跳過 |
|------|------|-------|--------|
| 1 | Memory Bank 同步 | `memory-updater` | ❌ |
| 2 | README 更新 | `readme-updater` | ✅ |
| 3 | CHANGELOG 更新 | `changelog-updater` | ✅ |
| 4 | ROADMAP 標記 | `roadmap-updater` | ✅ |
| 5 | 架構文檔（如有變更） | `ddd-architect` | ✅ |

## 第 1.1 條：Push 後檢查 CI 狀態

**⚠️ 強制執行 - 推送後必須檢查 CI 狀態**

1. **立即檢查**：執行 `git push` 後立刻檢查 GitHub Actions 執行狀態
2. **等待完成**：確認所有 CI 工作流程執行完畢
3. **修復失敗**：如有失敗，優先修復 CI 問題再繼續其他開發工作
4. **不可忽略**：CI 失敗視同破壞性變更，必須立即處理

### CI 檢查方法
- GitHub Web UI: `https://github.com/<repo>/actions`
- CLI: `gh run list --limit 1` 或 `gh run watch`

### 常見 CI 失敗原因
- 測試失敗
- Lint 錯誤（Ruff）
- Type 檢查錯誤（MyPy）
- 建置失敗

## 第 2 條：Commit Message 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 類型
- `feat`: 新功能
- `fix`: 修復
- `docs`: 文檔
- `refactor`: 重構
- `test`: 測試
- `chore`: 雜項

## 第 3 條：分支策略

| 分支 | 用途 | 保護 |
|------|------|------|
| `master` | 穩定版本 | ✅ |
| `develop` | 開發整合 | ✅ |
| `feature/*` | 功能開發 | ❌ |
| `hotfix/*` | 緊急修復 | ❌ |
