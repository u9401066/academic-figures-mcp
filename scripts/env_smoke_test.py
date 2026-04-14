from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from src.presentation.tools import generate_figure

ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def strip_optional_quotes(value: str) -> str:
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def parse_assignment(line: str) -> tuple[str, str] | None:
    normalized = line
    if normalized.startswith("export "):
        normalized = normalized[len("export ") :].strip()
    elif normalized.startswith("set "):
        normalized = normalized[len("set ") :].strip()

    if "=" not in normalized:
        return None

    key, value = normalized.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key or not ENV_KEY_PATTERN.match(key):
        return None
    return key, strip_optional_quotes(value)


def load_env_file(file_path: Path) -> dict[str, object]:
    recognized_assignments = 0
    unrecognized_non_comment_lines: list[int] = []

    lines = file_path.read_text(encoding="utf-8-sig").splitlines()
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        assignment = parse_assignment(line)
        if assignment is None:
            unrecognized_non_comment_lines.append(line_number)
            continue

        key, value = assignment
        os.environ[key] = value
        recognized_assignments += 1

    return {
        "recognized_assignments": recognized_assignments,
        "unrecognized_non_comment_lines": unrecognized_non_comment_lines,
    }


def infer_provider() -> str | None:
    provider = os.environ.get("AFM_IMAGE_PROVIDER", "").strip().lower()
    if provider in {"google", "openrouter"}:
        return provider
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter"
    if os.environ.get("GOOGLE_API_KEY"):
        return "google"
    return None


def presence_summary(provider: str | None) -> dict[str, object]:
    missing_required = (
        provider is None
        or (provider == "google" and not os.environ.get("GOOGLE_API_KEY"))
        or (provider == "openrouter" and not os.environ.get("OPENROUTER_API_KEY"))
    )
    return {
        "stage": "env load",
        "afm_image_provider": bool(os.environ.get("AFM_IMAGE_PROVIDER")),
        "google_api_key": bool(os.environ.get("GOOGLE_API_KEY")),
        "openrouter_api_key": bool(os.environ.get("OPENROUTER_API_KEY")),
        "openrouter_base_url": bool(os.environ.get("OPENROUTER_BASE_URL")),
        "gemini_model": bool(os.environ.get("GEMINI_MODEL")),
        "provider": provider,
        "missing_required_credential": missing_required,
    }


def classify_stage(message: str) -> str:
    lowered = message.lower()
    if any(token in lowered for token in ("pubmed", "ncbi", "fetch_paper", "eutils")):
        return "pubmed fetch"
    if any(
        token in lowered
        for token in ("openrouter", "gemini", "api", "model", "quota", "401", "403", "429")
    ):
        return "provider call"
    if any(
        token in lowered
        for token in (
            "save",
            "write",
            "output_path",
            "permission denied",
            "no such file or directory",
        )
    ):
        return "file write"
    if any(token in lowered for token in ("not set", "configuration", "credential", "api key")):
        return "dependency"
    return "other"


def sanitized_summary(result: dict[str, object]) -> dict[str, object]:
    return {
        "status": result.get("status"),
        "pmid": result.get("pmid"),
        "figure_type": result.get("figure_type"),
        "model": result.get("model"),
        "output_path": result.get("output_path"),
        "image_size_bytes": result.get("image_size_bytes"),
        "elapsed_seconds": result.get("elapsed_seconds"),
        "error": result.get("error"),
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {"stage": "env load", "error": "USAGE: env_smoke_test.py <env_path>"},
                ensure_ascii=False,
            )
        )
        return 1

    env_path = Path(sys.argv[1]).expanduser()
    if not env_path.exists():
        print(json.dumps({"stage": "env load", "error": "ENV_FILE_MISSING"}, ensure_ascii=False))
        return 1

    load_result = load_env_file(env_path)
    provider = infer_provider()
    if provider:
        os.environ["AFM_IMAGE_PROVIDER"] = provider

    summary = presence_summary(provider)
    print(json.dumps(summary, ensure_ascii=False))
    if (
        load_result["recognized_assignments"] == 0
        and load_result["unrecognized_non_comment_lines"]
    ):
        print(
            json.dumps(
                {
                    "stage": "env load",
                    "summary": {
                        "status": "error",
                        "error": "INVALID_ENV_FORMAT",
                        "recognized_assignments": load_result["recognized_assignments"],
                        "unrecognized_non_comment_lines": load_result[
                            "unrecognized_non_comment_lines"
                        ],
                        "example_file": "env.example",
                    },
                },
                ensure_ascii=False,
            )
        )
        return 1
    if summary["missing_required_credential"]:
        print(
            json.dumps(
                {
                    "stage": "env load",
                    "summary": {
                        "status": "error",
                        "error": "MISSING_REQUIRED_CREDENTIAL",
                        "recognized_assignments": load_result["recognized_assignments"],
                        "unrecognized_non_comment_lines": load_result[
                            "unrecognized_non_comment_lines"
                        ],
                        "example_file": "env.example",
                    },
                },
                ensure_ascii=False,
            )
        )
        return 1

    try:
        smoke_pmid = os.environ.get("AFM_SMOKE_PMID", "41657234").strip() or "41657234"
        result = generate_figure(pmid=smoke_pmid, language="zh-TW", output_size="1024x1024")
        compact = sanitized_summary(result)
        stage = "ok"
        if compact.get("status") in {"error", "generation_failed"}:
            stage = classify_stage(str(compact.get("error") or ""))
        print(json.dumps({"stage": stage, "summary": compact}, ensure_ascii=False))
        return 0 if compact.get("status") == "ok" else 1
    except Exception as exc:  # pragma: no cover - defensive smoke runner
        print(
            json.dumps(
                {
                    "stage": classify_stage(str(exc)),
                    "summary": {"status": "exception", "error": str(exc)[:500]},
                },
                ensure_ascii=False,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
