"""CLI entrypoint for CscGrader."""

from __future__ import annotations

import argparse
import json

from results.pipeline import CscGraderPipeline


def _add_common_timeout_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--build-timeout", type=int, default=30)
    parser.add_argument("--run-timeout", type=int, default=5)


def main() -> int:
    parser = argparse.ArgumentParser(prog="cscgrader")
    subparsers = parser.add_subparsers(dest="command", required=True)

    detect_parser = subparsers.add_parser("detect")
    detect_parser.add_argument("submission")

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("submission")
    build_parser.add_argument("--timeout", type=int, default=30)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("submission")
    run_parser.add_argument("--timeout", type=int, default=5)

    process_parser = subparsers.add_parser("process")
    process_parser.add_argument("submission")
    process_parser.add_argument("--output-dir", default="results")
    _add_common_timeout_args(process_parser)

    args = parser.parse_args()
    pipeline = CscGraderPipeline()

    if args.command == "detect":
        print(json.dumps(pipeline.detect_only(args.submission).__dict__, indent=2))
        return 0

    if args.command == "build":
        print(json.dumps(pipeline.build_only(args.submission, timeout_seconds=args.timeout).to_dict(), indent=2))
        return 0

    if args.command == "run":
        print(json.dumps(pipeline.run_only(args.submission, timeout_seconds=args.timeout).to_dict(), indent=2))
        return 0

    if args.command == "process":
        results = pipeline.process_path(
            args.submission,
            output_dir=args.output_dir,
            build_timeout_seconds=args.build_timeout,
            run_timeout_seconds=args.run_timeout,
        )
        print(json.dumps([result.to_dict() for result in results], indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
