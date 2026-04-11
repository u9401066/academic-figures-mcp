"""Legacy compatibility shim for the original src.server entry point."""

from __future__ import annotations

from src.presentation.server import main

if __name__ == "__main__":
    main()
