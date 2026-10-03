from __future__ import annotations

from pathlib import Path

from compilation.adapters import PythonAdapter
from compilation.service import BuildService
from execution.runner import ExecutionBackend
from execution.service import ExecutionService
from results.models import CommandResult, Status
from results.pipeline import CscGraderPipeline


class StubRunner(ExecutionBackend):
    def __init__(self, responses: list[CommandResult]) -> None:
        self.responses = responses
        self.commands: list[list[str]] = []

    def run(self, command: list[str], cwd: Path, timeout_seconds: int, env=None) -> CommandResult:
        self.commands.append(command)
        if not self.responses:
            raise AssertionError("No stubbed response available")
        return self.responses.pop(0)


def test_successful_compilation_and_execution(tmp_path: Path) -> None:
    sub = tmp_path / "StudentA"
    sub.mkdir()
    (sub / "main.py").write_text("print('ok')", encoding="utf-8")

    runner = StubRunner(
        [
            CommandResult("success", "python main.py", "ok\n", "", 0, 5, False),
        ]
    )
    result = CscGraderPipeline(runner=runner).process_submission(sub)

    assert result.overall_status == Status.EXECUTION_SUCCESS.value
    assert result.build is not None and result.build.status == "skipped"
    assert result.execution is not None and result.execution.status == "success"


def test_compilation_failure_stops_execution(tmp_path: Path) -> None:
    sub = tmp_path / "StudentB"
    sub.mkdir()
    (sub / "main.c").write_text("int main(){", encoding="utf-8")

    runner = StubRunner(
        [
            CommandResult("failed", "gcc main.c -o program", "", "error", 1, 3, False),
        ]
    )
    result = CscGraderPipeline(runner=runner).process_submission(sub)

    assert result.overall_status == Status.BUILD_FAILED.value
    assert result.execution is None


def test_runtime_failure(tmp_path: Path) -> None:
    sub = tmp_path / "StudentC"
    sub.mkdir()
    (sub / "main.py").write_text("raise SystemExit(1)", encoding="utf-8")

    runner = StubRunner(
        [
            CommandResult("failed", "python main.py", "", "boom", 1, 5, False),
        ]
    )
    result = CscGraderPipeline(runner=runner).run_only(sub)

    assert result.overall_status == Status.EXECUTION_FAILED.value


def test_timeout_handling(tmp_path: Path) -> None:
    sub = tmp_path / "StudentD"
    sub.mkdir()
    (sub / "main.py").write_text("while True: pass", encoding="utf-8")

    runner = StubRunner(
        [
            CommandResult("timeout", "python main.py", "", "", None, 5000, True),
        ]
    )
    result = CscGraderPipeline(runner=runner).run_only(sub, timeout_seconds=1)

    assert result.overall_status == Status.TIMEOUT.value


def test_build_and_execution_command_generation_with_services(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('x')", encoding="utf-8")
    runner = StubRunner([CommandResult("success", "python main.py", "", "", 0, 1, False)])

    build_result = BuildService(runner).build(PythonAdapter(), tmp_path, "main.py", timeout_seconds=5)
    exec_result = ExecutionService(runner).execute(PythonAdapter(), tmp_path, "main.py", timeout_seconds=5)

    assert build_result.status == "skipped"
    assert exec_result.command == "python main.py"


def test_multiple_submissions_continue_on_failure(tmp_path: Path) -> None:
    batch = tmp_path / "batch"
    batch.mkdir()

    ok = batch / "StudentGood"
    ok.mkdir()
    (ok / "main.py").write_text("print('ok')", encoding="utf-8")

    bad = batch / "StudentBad"
    bad.mkdir()
    (bad / "main.c").write_text("int main(){", encoding="utf-8")

    runner = StubRunner(
        [
            CommandResult("failed", "gcc main.c -o program", "", "compile error", 1, 4, False),
            CommandResult("success", "python main.py", "ok", "", 0, 4, False),
        ]
    )
    results = CscGraderPipeline(runner=runner).process_path(batch, output_dir=tmp_path / "out")
    statuses = {result.submission: result.overall_status for result in results}

    assert statuses["StudentBad"] == Status.BUILD_FAILED.value
    assert statuses["StudentGood"] == Status.EXECUTION_SUCCESS.value
    assert (tmp_path / "out" / "StudentBad.json").exists()
    assert (tmp_path / "out" / "StudentGood.json").exists()
