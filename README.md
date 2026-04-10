# 🎨 OpenClaw Illustrator MCP

Medical academic figure generator for VS Code Copilot.

## Install
```bash
pip install -e .
```

## VS Code Copilot Setup
Add to `.vscode/mcp.json` (or Copilot MCP settings):
```json
{
  "servers": {
    "illustrator": {
      "command": "illustrator-mcp",
      "env": {
        "GOOGLE_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Usage
Just tell Copilot naturally:
- "生成 PMID 41657234 的流程圖"
- "標題字改大一點"
- "幫我把箭頭換成紅色"
