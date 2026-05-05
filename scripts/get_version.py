"""Print the project version from pyproject.toml."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict-semver", action="store_true")
    args = parser.parse_args()

    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"\s*$', pyproject, re.MULTILINE)
    if not match:
        raise SystemExit("Could not find project.version in pyproject.toml")

    version = match.group(1)
    if args.strict_semver and not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit(f"Version is not strict X.Y.Z semver: {version}")

    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
