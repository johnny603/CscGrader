from __future__ import annotations

from pathlib import Path
import shutil

from execution.runner import LocalProcessRunner
from results.models import Status
from results.pipeline import CscGraderPipeline


FIXTURES_ROOT = Path(__file__).parent / "fixtures"
DUMMY_SUBMISSION = FIXTURES_ROOT / "dummy_submission"
DUMMY_ASSIGNMENT = FIXTURES_ROOT / "dummy_submission_assignment.json"


def _copy_fixture_submission(tmp_path: Path) -> Path:
    destination = tmp_path / "DummyStudent"
    shutil.copytree(DUMMY_SUBMISSION, destination)
    return destination


def test_dummy_submission_fixture_processes_end_to_end(tmp_path: Path) -> None:
    submission_dir = _copy_fixture_submission(tmp_path)
    output_dir = tmp_path / "results"

    pipeline = CscGraderPipeline(runner=LocalProcessRunner())
    results = pipeline.process_path(
        submission_dir,
        output_dir=output_dir,
        assignment=str(DUMMY_ASSIGNMENT),
        build_timeout_seconds=30,
        run_timeout_seconds=10,
    )

    assert len(results) == 3
    assert {result.part for result in results} == {"Part A", "Part B", "Part C"}
    assert all(result.overall_status == Status.EXECUTION_SUCCESS.value for result in results)

    by_part = {result.part: result for result in results}

    assert "BMI_ENGLISH=" in (by_part["Part A"].execution.stdout if by_part["Part A"].execution else "")
    assert "BMI_METRIC=" in (by_part["Part B"].execution.stdout if by_part["Part B"].execution else "")
    assert by_part["Part C"].execution is not None
    assert by_part["Part C"].execution.input_used is not None
    assert "English" in by_part["Part C"].execution.input_used

    for result in results:
        suffix = f"__{result.part}".replace(" ", "_")
        assert (output_dir / f"{result.submission}{suffix}.json").exists()


def test_dummy_submission_fixture_without_profile_uses_non_arbitrary_master_heuristic(tmp_path: Path) -> None:
    submission_dir = _copy_fixture_submission(tmp_path)

    result = CscGraderPipeline(runner=LocalProcessRunner()).process_submission(submission_dir)

    assert result.entrypoint == "BMI_CSC215_MASTER_DummyStudent.java"
    assert result.overall_status in {Status.EXECUTION_FAILED.value, Status.TIMEOUT.value}
    assert sorted(result.detected_entrypoints) == sorted(
        [
            "BMI_CSC215_English_DummyStudent.java",
            "BMI_CSC215_MASTER_DummyStudent.java",
            "BMI_CSC215_Metric_DummyStudent.java",
        ]
    )
    assert any(d.code in {"no_such_element_exception", "uncaught_exception", "non_zero_exit"} for d in result.diagnostics)
