---
description: "安全掃描 — OWASP + Bandit + Secrets 偵測"
mode: "agent"
tools: ['codebase', 'fetch', 'problems', 'runCommands', 'search']
---

# 安全掃描

請對專案執行全面安全掃描：

## 掃描步驟

### 1. Bandit 靜態分析
```bash
uv run bandit -r src/ -f json -o /tmp/bandit-report.json
uv run bandit -r src/ -f txt
```

### 2. OWASP Top 10 檢查
逐一檢查以下項目：
- A01: Broken Access Control
- A02: Cryptographic Failures
- A03: Injection
- A04: Insecure Design
- A05: Security Misconfiguration
- A06: Vulnerable and Outdated Components
- A07: Identification and Authentication Failures
- A08: Software and Data Integrity Failures
- A09: Security Logging and Monitoring Failures
- A10: Server-Side Request Forgery (SSRF)

### 3. Secrets 偵測
- 搜尋 hardcoded API keys, tokens, passwords
- 檢查 `.env` 檔案是否在 `.gitignore`
- 檢查 config 是否從環境變數讀取

### 4. 依賴漏洞
```bash
uv pip audit
```

## 輸出格式

```
## 🔒 安全掃描報告

### 風險摘要
| 等級 | 數量 |
|------|------|
| Critical | X |
| High | X |
| Medium | X |
| Low | X |

### 發現清單
1. **[Critical]** [描述] — 檔案:行號
   - 建議修正: ...

### 建議措施
- [ ] ...
```
