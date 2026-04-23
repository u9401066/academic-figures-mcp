"""Legacy compatibility shim for the original src.direct_run entry point."""

from __future__ import annotations

from src.bootstrap import direct_run_main as main

if __name__ == "__main__":
    main()
