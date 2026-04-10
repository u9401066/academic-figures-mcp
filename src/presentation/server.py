"""FastMCP server entry point — wires DDD layers together."""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("academic-figures", json_response=True)

# Register tools, resources, and prompts via submodules.
import src.presentation.prompts as _prompts  # noqa: F401, E402
import src.presentation.resources as _resources  # noqa: F401, E402
import src.presentation.tools as _tools  # noqa: F401, E402


def main() -> None:
    """Run the MCP server (stdio by default, override via MCP_TRANSPORT)."""
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport not in ("stdio", "sse", "streamable-http"):
        transport = "stdio"
    mcp.run(transport=transport)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
