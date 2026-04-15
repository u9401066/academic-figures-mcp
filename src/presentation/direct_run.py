"""Direct-run CLI for VS Code and local automation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.presentation import tools


def _load_payload_file(path: str) -> dict[str, object]:
    payload_path = Path(path)
    if not payload_path.exists():
        raise ValueError(f"Payload file not found: {payload_path}")
    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Payload file must contain valid JSON: {payload_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Payload file must contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(prog="afm-run")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan")
    plan_source = plan.add_mutually_exclusive_group(required=True)
    plan_source.add_argument("--pmid")
    plan_source.add_argument("--source-title")
    plan.add_argument("--source-summary")
    plan.add_argument("--source-kind", default="paper")
    plan.add_argument("--source-identifier")
    plan.add_argument("--figure-type", default="auto")
    plan.add_argument("--style-preset", default="journal_default")
    plan.add_argument("--language", default="zh-TW")
    plan.add_argument("--output-size", default="1024x1536")
    plan.add_argument("--output-format")
    plan.add_argument("--target-journal")
    plan.add_argument("--expected-label", action="append", dest="expected_labels")

    generate = subparsers.add_parser("generate")
    generate_source = generate.add_mutually_exclusive_group(required=True)
    generate_source.add_argument("--pmid")
    generate_source.add_argument("--source-title")
    generate_source.add_argument("--payload-file")
    generate.add_argument("--source-summary")
    generate.add_argument("--source-kind", default="paper")
    generate.add_argument("--source-identifier")
    generate.add_argument("--figure-type", default="auto")
    generate.add_argument("--language", default="zh-TW")
    generate.add_argument("--output-size", default="1024x1536")
    generate.add_argument("--output-format")
    generate.add_argument("--output-dir")
    generate.add_argument("--target-journal")

    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--image-path", required=True)
    evaluate.add_argument("--figure-type", default="infographic")
    evaluate.add_argument("--reference-pmid")

    verify = subparsers.add_parser("verify")
    verify.add_argument("--image-path", required=True)
    verify.add_argument("--figure-type", default="infographic")
    verify.add_argument("--language", default="zh-TW")
    verify.add_argument("--expected-label", action="append", dest="expected_labels")

    transform = subparsers.add_parser("transform")
    transform.add_argument("--image-path", required=True)
    transform.add_argument("--feedback", required=True)
    transform.add_argument("--output-path")
    transform.add_argument("--output-format")

    multi_turn_edit = subparsers.add_parser("multi-turn-edit")
    multi_turn_edit.add_argument("--image-path", required=True)
    multi_turn_edit.add_argument(
        "--instruction",
        action="append",
        dest="instructions",
        required=True,
    )
    multi_turn_edit.add_argument("--max-turns", type=int, default=5)

    batch = subparsers.add_parser("batch")
    batch.add_argument("--pmid", action="append", dest="pmids", required=True)
    batch.add_argument("--figure-type", default="auto")
    batch.add_argument("--language", default="zh-TW")
    batch.add_argument("--output-size", default="1024x1536")
    batch.add_argument("--output-dir")

    args = parser.parse_args()
    try:
        if args.command == "plan":
            result = tools.plan_figure(
                pmid=args.pmid,
                source_title=args.source_title,
                source_summary=args.source_summary,
                source_kind=args.source_kind,
                source_identifier=args.source_identifier,
                output_format=args.output_format,
                figure_type=args.figure_type,
                style_preset=args.style_preset,
                language=args.language,
                output_size=args.output_size,
                target_journal=args.target_journal,
                expected_labels=args.expected_labels,
            )
        elif args.command == "generate":
            payload = _load_payload_file(args.payload_file) if args.payload_file else None
            result = tools.generate_figure(
                pmid=args.pmid,
                source_title=args.source_title,
                source_summary=args.source_summary,
                source_kind=args.source_kind,
                source_identifier=args.source_identifier,
                planned_payload=payload,
                figure_type=args.figure_type,
                language=args.language,
                output_size=args.output_size,
                output_format=args.output_format,
                output_dir=args.output_dir,
                target_journal=args.target_journal,
            )
        elif args.command == "evaluate":
            result = tools.evaluate_figure(
                image_path=args.image_path,
                figure_type=args.figure_type,
                reference_pmid=args.reference_pmid,
            )
        elif args.command == "verify":
            result = tools.verify_figure(
                image_path=args.image_path,
                expected_labels=args.expected_labels,
                figure_type=args.figure_type,
                language=args.language,
            )
        elif args.command == "transform":
            result = tools.edit_figure(
                image_path=args.image_path,
                feedback=args.feedback,
                output_path=args.output_path,
                output_format=args.output_format,
            )
        elif args.command == "multi-turn-edit":
            result = tools.multi_turn_edit(
                image_path=args.image_path,
                instructions=args.instructions,
                max_turns=args.max_turns,
            )
        else:
            result = tools.batch_generate(
                pmids=args.pmids,
                figure_type=args.figure_type,
                language=args.language,
                output_size=args.output_size,
                output_dir=args.output_dir,
            )
    except ValueError as exc:
        result = {"status": "error", "error": str(exc)}

    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("status", "ok") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
