"""Core detect/build/execute processing pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from assignment.profiles import AssignmentProfileLoader
from compilation.adapters import AdapterRegistry
from compilation.service import BuildService
from detection.service import DetectionResult, Detector
from execution.runner import ExecutionBackend, LocalProcessRunner
from execution.service import ExecutionService
from results.diagnostics import diagnose_submission
from results.models import Status, SubmissionResult


class CscGraderPipeline:
    """Coordinates detection, build, execution, and result persistence."""

    def __init__(self, runner: ExecutionBackend | None = None) -> None:
        backend = runner or LocalProcessRunner()
        self.detector = Detector()
        self.registry = AdapterRegistry()
        self.builder = BuildService(backend)
        self.executor = ExecutionService(backend)
        self.assignment_loader = AssignmentProfileLoader()

    def detect_only(self, submission_dir: str | Path, preferred_entrypoint: str | None = None) -> DetectionResult:
        return self.detector.detect(submission_dir, preferred_entrypoint=preferred_entrypoint)

    def build_only(
        self,
        submission_dir: str | Path,
        timeout_seconds: int = 30,
        preferred_entrypoint: str | None = None,
    ) -> SubmissionResult:
        submission = Path(submission_dir)
        detected = self.detector.detect(submission, preferred_entrypoint=preferred_entrypoint)
        result = self._init_result(submission, detected)
        if not self._detection_ready(detected):
            result.overall_status = detected.status
            result.diagnostics = diagnose_submission(result, detected)
            return result

        adapter = self.registry.get(detected.language or "")
        if adapter is None or detected.entrypoint is None:
            result.overall_status = Status.UNSUPPORTED.value
            return result

        build = self.builder.build(adapter, submission, detected.entrypoint, timeout_seconds)
        result.build = build
        result.overall_status = Status.BUILD_SUCCESS.value if build.status in {"success", "skipped"} else Status.BUILD_FAILED.value
        if build.timed_out:
            result.overall_status = Status.TIMEOUT.value
        result.diagnostics = diagnose_submission(result, detected)
        return result

    def run_only(
        self,
        submission_dir: str | Path,
        timeout_seconds: int = 5,
        preferred_entrypoint: str | None = None,
        stdin_input: str | None = None,
        execution_command_override: list[str] | None = None,
    ) -> SubmissionResult:
        submission = Path(submission_dir)
        detected = self.detector.detect(submission, preferred_entrypoint=preferred_entrypoint)
        result = self._init_result(submission, detected)
        if not self._detection_ready(detected):
            result.overall_status = detected.status
            result.diagnostics = diagnose_submission(result, detected)
            return result

        adapter = self.registry.get(detected.language or "")
        if adapter is None or detected.entrypoint is None:
            result.overall_status = Status.UNSUPPORTED.value
            return result

        execution = self.executor.execute(
            adapter,
            submission,
            detected.entrypoint,
            timeout_seconds,
            stdin_input=stdin_input,
            command_override=execution_command_override,
        )
        result.execution = execution
        result.overall_status = Status.EXECUTION_SUCCESS.value if execution.status == "success" else Status.EXECUTION_FAILED.value
        if execution.timed_out:
            result.overall_status = Status.TIMEOUT.value
        result.diagnostics = diagnose_submission(result, detected)
        return result

    def process_submission(
        self,
        submission_dir: str | Path,
        build_timeout_seconds: int = 30,
        run_timeout_seconds: int = 5,
        preferred_entrypoint: str | None = None,
        stdin_input: str | None = None,
        assignment_name: str | None = None,
        part_name: str | None = None,
        run_command_override: list[str] | None = None,
    ) -> SubmissionResult:
        submission = Path(submission_dir)
        detected = self.detector.detect(submission, preferred_entrypoint=preferred_entrypoint)
        result = self._init_result(submission, detected, assignment_name=assignment_name, part_name=part_name)
        if not self._detection_ready(detected):
            result.overall_status = detected.status
            result.diagnostics = diagnose_submission(result, detected)
            return result

        adapter = self.registry.get(detected.language or "")
        if adapter is None or detected.entrypoint is None:
            result.overall_status = Status.UNSUPPORTED.value
            return result

        build = self.builder.build(adapter, submission, detected.entrypoint, build_timeout_seconds)
        result.build = build
        if build.timed_out:
            result.overall_status = Status.TIMEOUT.value
            result.diagnostics = diagnose_submission(result, detected)
            return result

        if build.status not in {"success", "skipped"}:
            result.overall_status = Status.BUILD_FAILED.value
            result.diagnostics = diagnose_submission(result, detected)
            return result

        execution = self.executor.execute(
            adapter,
            submission,
            detected.entrypoint,
            run_timeout_seconds,
            stdin_input=stdin_input,
            command_override=run_command_override,
        )
        result.execution = execution
        result.overall_status = Status.EXECUTION_SUCCESS.value if execution.status == "success" else Status.EXECUTION_FAILED.value
        if execution.timed_out:
            result.overall_status = Status.TIMEOUT.value

        result.diagnostics = diagnose_submission(result, detected)
        return result

    def process_path(
        self,
        path: str | Path,
        output_dir: str | Path = "results",
        build_timeout_seconds: int = 30,
        run_timeout_seconds: int = 5,
        assignment: str | None = None,
        stdin_input: str | None = None,
    ) -> list[SubmissionResult]:
        root = Path(path)
        results: list[SubmissionResult] = []
        submissions = self._resolve_submissions(root)

        profile = self.assignment_loader.load(assignment)

        for submission in submissions:
            if profile:
                resolved = self.assignment_loader.resolve_for_submission(profile, submission)
                for part in resolved.parts:
                    part_input = part.input_text if part.input_text is not None else stdin_input
                    result = self.process_submission(
                        submission,
                        build_timeout_seconds=build_timeout_seconds,
                        run_timeout_seconds=run_timeout_seconds,
                        preferred_entrypoint=part.entrypoint,
                        stdin_input=part_input,
                        assignment_name=resolved.name,
                        part_name=part.name,
                        run_command_override=part.run_command,
                    )
                    self.save_result(result, output_dir)
                    results.append(result)
            else:
                result = self.process_submission(
                    submission,
                    build_timeout_seconds=build_timeout_seconds,
                    run_timeout_seconds=run_timeout_seconds,
                    stdin_input=stdin_input,
                )
                self.save_result(result, output_dir)
                results.append(result)

        return results

    def save_result(self, result: SubmissionResult, output_dir: str | Path) -> Path:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        suffix = f"__{result.part}" if result.part else ""
        safe_suffix = suffix.replace(" ", "_")
        output_path = out / f"{result.submission}{safe_suffix}.json"
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

    @staticmethod
    def _detection_ready(detection: DetectionResult) -> bool:
        return detection.status == Status.DETECTED.value and bool(detection.language and detection.entrypoint)

    @staticmethod
    def _init_result(
        submission: Path,
        detection: DetectionResult,
        assignment_name: str | None = None,
        part_name: str | None = None,
    ) -> SubmissionResult:
        return SubmissionResult(
            submission=submission.name,
            language=detection.language,
            entrypoint=detection.entrypoint,
            detection_status=detection.status,
            overall_status=detection.status,
            assignment=assignment_name,
            part=part_name,
            detected_entrypoints=detection.entrypoints,
        )
