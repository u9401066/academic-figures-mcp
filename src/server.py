"""Legacy compatibility shim for the original src.server entry point."""

from __future__ import annotations

from src.bootstrap import server_main as main

if __name__ == "__main__":
    main()
