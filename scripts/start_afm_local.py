"""Cross-platform local launcher for afm-server and afm-run."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"Env file not found: {path}")

    loaded: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].strip()
        elif line.startswith("set "):
            line = line[4:].strip()

        name, separator, value = line.partition("=")
        if not separator:
            continue

        normalized_name = name.strip()
        if not normalized_name:
            continue

        loaded[normalized_name] = strip_matching_quotes(value.strip())

    return loaded


def strip_matching_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def build_command(repo_root: Path, mode: str, passthrough: list[str]) -> list[str]:
    module = "src.presentation.server" if mode == "server" else "src.presentation.direct_run"
    return [
        "uv",
        "run",
        "--project",
        str(repo_root),
        "python",
        "-m",
        module,
        *passthrough,
    ]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="start_afm_local.py")
    parser.add_argument("mode", nargs="?", choices=("server", "run"), default="server")
    parser.add_argument("--env-file", default="env")
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if shutil.which("uv") is None:
        raise SystemExit("uv is required on PATH to launch Academic Figures MCP")

    repo_root = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env.update(parse_env_file(repo_root / args.env_file))

    passthrough = list(args.arguments)
    if passthrough[:1] == ["--"]:
        passthrough = passthrough[1:]

    command = build_command(repo_root, args.mode, passthrough)
    completed = subprocess.run(command, cwd=repo_root, env=env, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())