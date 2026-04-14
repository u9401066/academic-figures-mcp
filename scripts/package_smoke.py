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
        planned_payload_path = tmp_path / "planned_payload.json"
        output_dir = tmp_path / "outputs"
        manifest_dir = tmp_path / "manifests"
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest_dir.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env.update(
            {
                "UV_NO_PROGRESS": "1",
                "AFM_METADATA_SOURCE": "file",
                "AFM_METADATA_FILE": str(metadata_path),
                "AFM_IMAGE_PROVIDER": "stub",
                "AFM_OUTPUT_DIR": str(output_dir),
                "AFM_MANIFEST_DIR": str(manifest_dir),
                "PYTHONIOENCODING": "utf-8",
                "PYTHONUTF8": "1",
            }
        )

        help_result = _run(["uvx", "--from", ".", "afm-run", "--help"], repo_root, env)
        if help_result.returncode != 0:
            return _fail("help", help_result, "uvx package entrypoint failed")

        if "usage: afm-run" not in help_result.stdout:
            return _fail("help", help_result, "afm-run help output missing expected usage text")

        plan_result = _run(
            ["uvx", "--from", ".", "afm-run", "plan", "--pmid", SMOKE_PMID],
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

        planned_payload_path.write_text(
            json.dumps(payload["planned_payload"]),
            encoding="utf-8",
        )

        generate_result = _run(
            [
                "uvx",
                "--from",
                ".",
                "afm-run",
                "generate",
                "--payload-file",
                str(planned_payload_path),
                "--output-dir",
                str(output_dir),
            ],
            repo_root,
            env,
        )
        if generate_result.returncode != 0:
            return _fail("generate", generate_result, "package-mode generation smoke failed")

        try:
            generate_payload = json.loads(generate_result.stdout)
        except json.JSONDecodeError:
            return _fail(
                "generate",
                generate_result,
                "package-mode generation smoke returned invalid JSON",
            )

        if generate_payload.get("status") != "ok":
            return _fail("generate", generate_result, "generation smoke returned non-ok status")

        output_path = Path(str(generate_payload.get("output_path", "")))
        if not output_path.exists():
            return _fail("generate", generate_result, "generation smoke did not write output_path")

        if output_path.stat().st_size == 0:
            return _fail("generate", generate_result, "generated image is empty")

        manifest_files = sorted(manifest_dir.glob("*.json"))
        if not manifest_files:
            return _fail("generate", generate_result, "generation did not write manifest files")

        verify_result = _run(
            [
                "uvx",
                "--from",
                ".",
                "afm-run",
                "verify",
                "--image-path",
                str(output_path),
                "--expected-label",
                "stub figure",
            ],
            repo_root,
            env,
        )
        if verify_result.returncode != 0:
            return _fail("verify", verify_result, "package-mode verify smoke failed")

        try:
            verify_payload = json.loads(verify_result.stdout)
        except json.JSONDecodeError:
            return _fail("verify", verify_result, "package-mode verify returned invalid JSON")

        if verify_payload.get("status") != "ok":
            return _fail("verify", verify_result, "verify smoke returned non-ok status")

        if verify_payload.get("passed") is not True:
            return _fail("verify", verify_result, "verify smoke did not pass quality gate")

        summary = {
            "stage": "package-smoke",
            "status": "ok",
            "pmid": payload.get("pmid"),
            "selected_figure_type": payload.get("selected_figure_type"),
            "render_route": payload.get("render_route"),
            "output_path": str(output_path),
            "manifest_count": len(manifest_files),
        }
        print(json.dumps(summary, ensure_ascii=False))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
