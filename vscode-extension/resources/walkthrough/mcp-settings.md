# Insert MCP Settings

The extension can automatically write a `.vscode/mcp.json` file so that VS Code knows how to start the Academic Figures MCP server.

## What Gets Created

```json
{
  "servers": {
    "academic-figures": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--project", "${workspaceFolder}", "python", "-m", "src.presentation.server"],
      "env": {
        "AFM_IMAGE_PROVIDER": "${env:AFM_IMAGE_PROVIDER}",
        "GOOGLE_API_KEY": "${env:GOOGLE_API_KEY}",
        "OPENROUTER_API_KEY": "${env:OPENROUTER_API_KEY}",
        "OPENROUTER_BASE_URL": "${env:OPENROUTER_BASE_URL}",
        "OPENROUTER_HTTP_REFERER": "${env:OPENROUTER_HTTP_REFERER}",
        "OPENROUTER_APP_TITLE": "${env:OPENROUTER_APP_TITLE}",
        "GEMINI_MODEL": "${env:GEMINI_MODEL}"
      }
    }
  }
}
```

## Two Modes

| Mode | How it works |
| ---- | ------------ |
| **Extension Provider** | MCP server is registered automatically via the proposed API. Provider selection comes from extension settings, and credentials can come from SecretStorage, a configured env file, or process env. |
| **Static Config** | `.vscode/mcp.json` uses a shell-neutral `uv --project ${workspaceFolder}` launch so the same config works across Windows, macOS, and Linux. |

Both modes can coexist. The extension provider takes precedence when available.
