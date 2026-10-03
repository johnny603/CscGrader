"""Core detect/build/execute processing pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from compilation.adapters import AdapterRegistry
from compilation.service import BuildService
from detection.service import DetectionResult, Detector
from execution.runner import ExecutionBackend, LocalProcessRunner
from execution.service import ExecutionService
from results.models import Status, SubmissionResult


class CscGraderPipeline:
    """Coordinates detection, build, execution, and result persistence."""

    def __init__(self, runner: ExecutionBackend | None = None) -> None:
        backend = runner or LocalProcessRunner()
        self.detector = Detector()
        self.registry = AdapterRegistry()
        self.builder = BuildService(backend)
        self.executor = ExecutionService(backend)

    def detect_only(self, submission_dir: str | Path) -> DetectionResult:
        return self.detector.detect(submission_dir)

    def build_only(self, submission_dir: str | Path, timeout_seconds: int = 30) -> SubmissionResult:
        submission = Path(submission_dir)
        detected = self.detector.detect(submission)
        if detected.status != Status.DETECTED.value or not detected.language or not detected.entrypoint:
            return SubmissionResult(
                submission=submission.name,
                language=detected.language,
                entrypoint=detected.entrypoint,
                detection_status=detected.status,
                overall_status=detected.status,
            )

        adapter = self.registry.get(detected.language)
        if adapter is None:
            return SubmissionResult(
                submission=submission.name,
                language=detected.language,
                entrypoint=detected.entrypoint,
                detection_status=Status.DETECTED.value,
                overall_status=Status.UNSUPPORTED.value,
            )

        build = self.builder.build(adapter, submission, detected.entrypoint, timeout_seconds)
        status = Status.BUILD_SUCCESS.value if build.status in {"success", "skipped"} else Status.BUILD_FAILED.value
        if build.timed_out:
            status = Status.TIMEOUT.value
        return SubmissionResult(
            submission=submission.name,
            language=detected.language,
            entrypoint=detected.entrypoint,
            detection_status=Status.DETECTED.value,
            overall_status=status,
            build=build,
        )

    def run_only(self, submission_dir: str | Path, timeout_seconds: int = 5) -> SubmissionResult:
        submission = Path(submission_dir)
        detected = self.detector.detect(submission)
        if detected.status != Status.DETECTED.value or not detected.language or not detected.entrypoint:
            return SubmissionResult(
                submission=submission.name,
                language=detected.language,
                entrypoint=detected.entrypoint,
                detection_status=detected.status,
                overall_status=detected.status,
            )

        adapter = self.registry.get(detected.language)
        if adapter is None:
            return SubmissionResult(
                submission=submission.name,
                language=detected.language,
                entrypoint=detected.entrypoint,
                detection_status=Status.DETECTED.value,
                overall_status=Status.UNSUPPORTED.value,
            )

        execution = self.executor.execute(adapter, submission, detected.entrypoint, timeout_seconds)
        status = Status.EXECUTION_SUCCESS.value if execution.status == "success" else Status.EXECUTION_FAILED.value
        if execution.timed_out:
            status = Status.TIMEOUT.value
        return SubmissionResult(
            submission=submission.name,
            language=detected.language,
            entrypoint=detected.entrypoint,
            detection_status=Status.DETECTED.value,
            overall_status=status,
            execution=execution,
        )

    def process_submission(
        self,
        submission_dir: str | Path,
        build_timeout_seconds: int = 30,
        run_timeout_seconds: int = 5,
    ) -> SubmissionResult:
        submission = Path(submission_dir)
        detected = self.detector.detect(submission)
        if detected.status != Status.DETECTED.value or not detected.language or not detected.entrypoint:
            return SubmissionResult(
                submission=submission.name,
                language=detected.language,
                entrypoint=detected.entrypoint,
                detection_status=detected.status,
                overall_status=detected.status,
            )

        adapter = self.registry.get(detected.language)
        if adapter is None:
            return SubmissionResult(
                submission=submission.name,
                language=detected.language,
                entrypoint=detected.entrypoint,
                detection_status=Status.DETECTED.value,
                overall_status=Status.UNSUPPORTED.value,
            )

        build = self.builder.build(adapter, submission, detected.entrypoint, build_timeout_seconds)
        if build.timed_out:
            return SubmissionResult(
                submission=submission.name,
                language=detected.language,
                entrypoint=detected.entrypoint,
                detection_status=Status.DETECTED.value,
                overall_status=Status.TIMEOUT.value,
                build=build,
            )

        if build.status not in {"success", "skipped"}:
            return SubmissionResult(
                submission=submission.name,
                language=detected.language,
                entrypoint=detected.entrypoint,
                detection_status=Status.DETECTED.value,
                overall_status=Status.BUILD_FAILED.value,
                build=build,
            )

        execution = self.executor.execute(adapter, submission, detected.entrypoint, run_timeout_seconds)
        status = Status.EXECUTION_SUCCESS.value if execution.status == "success" else Status.EXECUTION_FAILED.value
        if execution.timed_out:
            status = Status.TIMEOUT.value

        return SubmissionResult(
            submission=submission.name,
            language=detected.language,
            entrypoint=detected.entrypoint,
            detection_status=Status.DETECTED.value,
            overall_status=status,
            build=build,
            execution=execution,
        )

    def process_path(
        self,
        path: str | Path,
        output_dir: str | Path = "results",
        build_timeout_seconds: int = 30,
        run_timeout_seconds: int = 5,
    ) -> list[SubmissionResult]:
        root = Path(path)
        results: list[SubmissionResult] = []

        submissions = self._resolve_submissions(root)
        for submission in submissions:
            result = self.process_submission(
                submission,
                build_timeout_seconds=build_timeout_seconds,
                run_timeout_seconds=run_timeout_seconds,
            )
            self.save_result(result, output_dir)
            results.append(result)
        return results

    def save_result(self, result: SubmissionResult, output_dir: str | Path) -> Path:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        output_path = out / f"{result.submission}.json"
        output_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        return output_path

    def _resolve_submissions(self, path: Path) -> list[Path]:
        path = path.resolve()
        if not path.exists():
            return [path]
        if not path.is_dir():
            return [path]

        direct_files = [p for p in path.iterdir() if p.is_file()]
        if direct_files:
            return [path]

        children = [p for p in path.iterdir() if p.is_dir()]
        return sorted(children) if children else [path]
