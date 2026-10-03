from __future__ import annotations

import json
from pathlib import Path

from execution.runner import ExecutionBackend
from results.models import CommandResult, Status
from results.pipeline import CscGraderPipeline


class StubRunner(ExecutionBackend):
    def __init__(self, responses: list[CommandResult]) -> None:
        self.responses = responses
        self.commands: list[list[str]] = []
        self.stdin_inputs: list[str | None] = []

    def run(self, command: list[str], cwd: Path, timeout_seconds: int, env=None, stdin_input=None) -> CommandResult:
        self.commands.append(command)
        self.stdin_inputs.append(stdin_input)
        if not self.responses:
            raise AssertionError("No stubbed response available")
        return self.responses.pop(0)


def _write_java_main(path: Path, class_name: str) -> None:
    path.write_text(
        f"public class {class_name} {{ public static void main(String[] args) {{}} }}",
        encoding="utf-8",
    )


def test_compilation_failure_stops_execution(tmp_path: Path) -> None:
    sub = tmp_path / "StudentB"
    sub.mkdir()
    _write_java_main(sub / "Main.java", "Main")

    runner = StubRunner([CommandResult("failed", "javac Main.java", "", "error: ';' expected", 1, 3, False)])
    result = CscGraderPipeline(runner=runner).process_submission(sub)

    assert result.overall_status == Status.BUILD_FAILED.value
    assert result.execution is None
    assert any(d.code == "syntax_error" for d in result.diagnostics)


def test_runtime_exception_diagnostic(tmp_path: Path) -> None:
    sub = tmp_path / "StudentC"
    sub.mkdir()
    _write_java_main(sub / "Main.java", "Main")

    runner = StubRunner(
        [
            CommandResult("success", "javac Main.java", "", "", 0, 3, False),
            CommandResult("failed", "java Main", "", "java.lang.RuntimeException: boom", 1, 5, False),
        ]
    )
    result = CscGraderPipeline(runner=runner).process_submission(sub)

    assert result.overall_status == Status.EXECUTION_FAILED.value
    assert any(d.code == "uncaught_exception" for d in result.diagnostics)


def test_nosuchelement_with_stdin_marks_likely_input_exhaustion(tmp_path: Path) -> None:
    sub = tmp_path / "StudentD"
    sub.mkdir()
    _write_java_main(sub / "Main.java", "Main")

    runner = StubRunner(
        [
            CommandResult("success", "javac Main.java", "", "", 0, 3, False),
            CommandResult(
                "failed",
                "java Main",
                "",
                "java.util.NoSuchElementException",
                1,
                5,
                False,
                input_used="English\n25\n180\n!\n",
            ),
        ]
    )
    result = CscGraderPipeline(runner=runner).process_submission(sub, stdin_input="English\n25\n180\n!\n")

    assert result.execution is not None
    assert result.execution.input_used is not None
    assert any(d.code == "no_such_element_exception" and d.likely for d in result.diagnostics)


def test_timeout_handling(tmp_path: Path) -> None:
    sub = tmp_path / "StudentE"
    sub.mkdir()
    _write_java_main(sub / "Main.java", "Main")

    runner = StubRunner(
        [
            CommandResult("success", "javac Main.java", "", "", 0, 3, False),
            CommandResult("timeout", "java Main", "", "", None, 5000, True),
        ]
    )
    result = CscGraderPipeline(runner=runner).process_submission(sub, run_timeout_seconds=1)

    assert result.overall_status == Status.TIMEOUT.value
    assert any(d.code == "timeout" for d in result.diagnostics)


def test_assignment_profile_master_english_metric(tmp_path: Path) -> None:
    sub = tmp_path / "BenjaminSlye"
    sub.mkdir()
    _write_java_main(sub / "BMI_CSC215_English_BenjaminSlye.java", "BMI_CSC215_English_BenjaminSlye")
    _write_java_main(sub / "BMI_CSC215_Metric_BenjaminSlye.java", "BMI_CSC215_Metric_BenjaminSlye")
    _write_java_main(sub / "BMI_CSC215_MASTER_BenjaminSlye.java", "BMI_CSC215_MASTER_BenjaminSlye")

    profile = {
        "name": "CSC 215 Assignment 03",
        "parts": [
            {"name": "Part A", "entrypoint": "BMI_CSC215_English_{student}.java"},
            {"name": "Part B", "entrypoint": "BMI_CSC215_Metric_{student}.java"},
            {
                "name": "Part C",
                "entrypoint": "BMI_CSC215_MASTER_{student}.java",
                "dependencies": [
                    "BMI_CSC215_English_{student}.java",
                    "BMI_CSC215_Metric_{student}.java",
                ],
            },
        ],
    }
    profile_path = tmp_path / "csc215-assignment-03.json"
    profile_path.write_text(json.dumps(profile), encoding="utf-8")

    responses: list[CommandResult] = []
    for _ in range(3):
        responses.append(CommandResult("success", "javac ...", "", "", 0, 2, False))
        responses.append(CommandResult("success", "java ...", "ok", "", 0, 2, False))

    results = CscGraderPipeline(runner=StubRunner(responses)).process_path(sub, output_dir=tmp_path / "out", assignment=str(profile_path))

    assert len(results) == 3
    assert {r.part for r in results} == {"Part A", "Part B", "Part C"}
    assert all(r.overall_status == Status.EXECUTION_SUCCESS.value for r in results)


def test_filename_public_class_mismatch_diagnostic(tmp_path: Path) -> None:
    sub = tmp_path / "Mismatch"
    sub.mkdir()
    _write_java_main(sub / "wrongName.java", "RightName")

    runner = StubRunner(
        [
            CommandResult(
                "failed",
                "javac wrongName.java",
                "",
                "error: class RightName is public, should be declared in a file named RightName.java",
                1,
                3,
                False,
            )
        ]
    )
    result = CscGraderPipeline(runner=runner).build_only(sub, preferred_entrypoint="wrongName.java")

    assert result.overall_status == Status.BUILD_FAILED.value
    assert any(d.code == "filename_public_class_mismatch" for d in result.diagnostics)


def test_missing_dependency_diagnostic(tmp_path: Path) -> None:
    sub = tmp_path / "MissingDep"
    sub.mkdir()
    _write_java_main(sub / "Main.java", "Main")

    runner = StubRunner([CommandResult("failed", "javac Main.java", "", "error: package helper does not exist", 1, 3, False)])
    result = CscGraderPipeline(runner=runner).build_only(sub)

    assert any(d.code == "missing_dependency" for d in result.diagnostics)


def test_successful_java_run_adds_likely_ide_note(tmp_path: Path) -> None:
    sub = tmp_path / "WorksInTerminal"
    sub.mkdir()
    _write_java_main(sub / "Main.java", "Main")

    runner = StubRunner(
        [
            CommandResult("success", "javac Main.java", "", "", 0, 2, False),
            CommandResult("success", "java Main", "ok", "", 0, 2, False),
        ]
    )
    result = CscGraderPipeline(runner=runner).process_submission(sub)

    assert result.overall_status == Status.EXECUTION_SUCCESS.value
    assert any(d.code == "likely_ide_configuration_issue" for d in result.diagnostics)


def test_multiple_submissions_continue_on_failure(tmp_path: Path) -> None:
    batch = tmp_path / "batch"
    batch.mkdir()

    ok = batch / "StudentGood"
    ok.mkdir()
    _write_java_main(ok / "Main.java", "Main")

    bad = batch / "StudentBad"
    bad.mkdir()
    _write_java_main(bad / "Main.java", "Main")

    runner = StubRunner(
        [
            CommandResult("failed", "javac Main.java", "", "error: cannot find symbol", 1, 4, False),
            CommandResult("success", "javac Main.java", "", "", 0, 4, False),
            CommandResult("success", "java Main", "ok", "", 0, 4, False),
        ]
    )
    results = CscGraderPipeline(runner=runner).process_path(batch, output_dir=tmp_path / "out")
    statuses = {result.submission: result.overall_status for result in results}

    assert statuses["StudentBad"] == Status.BUILD_FAILED.value
    assert statuses["StudentGood"] == Status.EXECUTION_SUCCESS.value
    assert (tmp_path / "out" / "StudentBad.json").exists()
    assert (tmp_path / "out" / "StudentGood.json").exists()
