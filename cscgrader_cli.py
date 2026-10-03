"""CLI entrypoint for CscGrader."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from results.pipeline import CscGraderPipeline


def _add_common_timeout_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--build-timeout", type=int, default=30)
    parser.add_argument("--run-timeout", type=int, default=5)


def _read_input_text(input_path: str | None) -> str | None:
    if not input_path:
        return None
    return Path(input_path).read_text(encoding="utf-8")


def _status_mark(status: str) -> str:
    return "✓" if status in {"detected", "build_success", "execution_success"} else "✗"


def _print_concise_summary(results: list[dict]) -> None:
    grouped: dict[str, list[dict]] = {}
    for result in results:
        grouped.setdefault(result["submission"], []).append(result)

    for submission, entries in grouped.items():
        first = entries[0]
        assignment = first.get("assignment")
        print(f"Student: {submission}")
        if assignment:
            print(f"Assignment: {assignment}")
        print("")

        for entry in entries:
            label = entry.get("part") or "Submission"
            print(label)
            print(f"  {_status_mark(entry['detection_status'])} Discovered")

            build = entry.get("build")
            if build:
                print(f"  {'✓' if build['status'] in {'success', 'skipped'} else '✗'} Compiled")
            execution = entry.get("execution")
            if execution:
                print(f"  {'✓' if execution['status'] == 'success' else '✗'} Executed")

            diagnostics = entry.get("diagnostics") or []
            if diagnostics:
                print("  Diagnosis:")
                for diagnostic in diagnostics:
                    print(f"    - {diagnostic['code']}: {diagnostic['message']}")
            print("")


def main() -> int:
    parser = argparse.ArgumentParser(prog="cscgrader")
    subparsers = parser.add_subparsers(dest="command", required=True)

    detect_parser = subparsers.add_parser("detect")
    detect_parser.add_argument("submission")
    detect_parser.add_argument("--entrypoint")

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("submission")
    build_parser.add_argument("--timeout", type=int, default=30)
    build_parser.add_argument("--entrypoint")

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("submission")
    run_parser.add_argument("--timeout", type=int, default=5)
    run_parser.add_argument("--entrypoint")
    run_parser.add_argument("--input")

    process_parser = subparsers.add_parser("process")
    process_parser.add_argument("submission")
    process_parser.add_argument("--output-dir", default="results")
    process_parser.add_argument("--assignment")
    process_parser.add_argument("--input")
    _add_common_timeout_args(process_parser)

    batch_parser = subparsers.add_parser("batch")
    batch_parser.add_argument("submissions")
    batch_parser.add_argument("--output-dir", default="results")
    batch_parser.add_argument("--assignment")
    batch_parser.add_argument("--input")
    _add_common_timeout_args(batch_parser)

    args = parser.parse_args()
    pipeline = CscGraderPipeline()

    if args.command == "detect":
        result = pipeline.detect_only(args.submission, preferred_entrypoint=args.entrypoint)
        print(json.dumps(result.__dict__, indent=2))
        return 0

    if args.command == "build":
        result = pipeline.build_only(
            args.submission,
            timeout_seconds=args.timeout,
            preferred_entrypoint=args.entrypoint,
        )
        print(json.dumps(result.to_dict(), indent=2))
        return 0

    if args.command == "run":
        result = pipeline.run_only(
            args.submission,
            timeout_seconds=args.timeout,
            preferred_entrypoint=args.entrypoint,
            stdin_input=_read_input_text(args.input),
        )
        print(json.dumps(result.to_dict(), indent=2))
        return 0

    if args.command in {"process", "batch"}:
        target = args.submission if args.command == "process" else args.submissions
        results = pipeline.process_path(
            target,
            output_dir=args.output_dir,
            build_timeout_seconds=args.build_timeout,
            run_timeout_seconds=args.run_timeout,
            assignment=args.assignment,
            stdin_input=_read_input_text(args.input),
        )
        data = [result.to_dict() for result in results]
        _print_concise_summary(data)
        print(json.dumps(data, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
