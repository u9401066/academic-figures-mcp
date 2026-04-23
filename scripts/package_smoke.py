"""Cross-platform package-mode smoke test for Academic Figures MCP."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

SMOKE_PMID = "41657234"
SMOKE_METADATA = {
    SMOKE_PMID: {
        "title": "Airway rescue workflow",
        "authors": "Example Author",
        "journal": "Journal of Testing",
        "abstract": "A structured airway rescue algorithm.",
    }
}


def _run(command: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _fail(stage: str, result: subprocess.CompletedProcess[str] | None, message: str) -> int:
    payload = {
        "stage": stage,
        "status": "error",
        "message": message,
    }
    if result is not None:
        payload["returncode"] = result.returncode
        payload["stdout"] = result.stdout[-2000:]
        payload["stderr"] = result.stderr[-2000:]
    print(json.dumps(payload, ensure_ascii=False))
    return 1


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent

    with tempfile.TemporaryDirectory(prefix="afm-package-smoke-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        metadata_path = tmp_path / "papers.json"
        metadata_path.write_text(json.dumps(SMOKE_METADATA), encoding="utf-8")

        env = os.environ.copy()
        env.update(
            {
                "UV_NO_PROGRESS": "1",
                "AFM_METADATA_SOURCE": "file",
                "AFM_METADATA_FILE": str(metadata_path),
                "PYTHONIOENCODING": "utf-8",
                "PYTHONUTF8": "1",
            }
        )

        help_result = _run(
            ["uvx", "--no-cache", "--from", ".", "afm-run", "--help"],
            repo_root,
            env,
        )
        if help_result.returncode != 0:
            return _fail("help", help_result, "uvx package entrypoint failed")

        if "usage: afm-run" not in help_result.stdout:
            return _fail("help", help_result, "afm-run help output missing expected usage text")

        plan_result = _run(
            [
                "uvx",
                "--no-cache",
                "--from",
                ".",
                "afm-run",
                "plan",
                "--pmid",
                SMOKE_PMID,
                "--target-journal",
                "Nature",
            ],
            repo_root,
            env,
        )
        if plan_result.returncode != 0:
            return _fail("plan", plan_result, "package-mode planning smoke failed")

        try:
            payload = json.loads(plan_result.stdout)
        except json.JSONDecodeError:
            return _fail("plan", plan_result, "package-mode planning smoke returned invalid JSON")

        if payload.get("status") != "ok":
            return _fail("plan", plan_result, "package-mode planning smoke returned non-ok status")

        if payload.get("pmid") != SMOKE_PMID:
            return _fail(
                "plan",
                plan_result,
                "package-mode planning smoke returned unexpected PMID",
            )

        if not payload.get("selected_figure_type"):
            return _fail("plan", plan_result, "planning smoke did not classify a figure type")

        if not isinstance(payload.get("planned_payload"), dict):
            return _fail("plan", plan_result, "planning smoke did not return planned_payload")

        journal_profile = payload.get("journal_profile")
        if (
            not isinstance(journal_profile, dict)
            or journal_profile.get("id") != "nature_portfolio"
        ):
            return _fail(
                "plan",
                plan_result,
                "package-mode planning smoke did not load installed journal profiles",
            )

        summary = {
            "stage": "package-smoke",
            "status": "ok",
            "pmid": payload.get("pmid"),
            "selected_figure_type": payload.get("selected_figure_type"),
            "render_route": payload.get("render_route"),
            "journal_profile": journal_profile.get("id"),
        }
        print(json.dumps(summary, ensure_ascii=False))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
