"""End-to-end smoke test for the dummy submission fixture."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "dummy_submission"
PROFILE = REPO / "tests" / "fixtures" / "dummy_submission_assignment.json"

EXPECTED_ENTRYPOINTS = {
    "BMI_CSC215_English_DummyStudent.java",
    "BMI_CSC215_Metric_DummyStudent.java",
    "BMI_CSC215_MASTER_DummyStudent.java",
}


@pytest.fixture(scope="module")
def smoke_output(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("cscgrader-smoke")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "cscgrader_cli",
            "process",
            str(FIXTURE),
            "--assignment",
            str(PROFILE),
            "--output-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return out_dir, proc.stdout


def test_smoke_produces_json(smoke_output):
    out_dir, _ = smoke_output
    assert list(out_dir.glob("*.json")), "no JSON evidence produced"


def test_no_detection_failures(smoke_output):
    out_dir, _ = smoke_output
    for path in out_dir.glob("*.json"):
        result = json.loads(path.read_text())
        assert result["overall_status"] != "detection_failed", result
        messages = [d["message"] for d in result.get("diagnostics", [])]
        assert not any("dummysubmission" in m for m in messages), messages


def test_entrypoints_use_dummystudent(smoke_output):
    out_dir, _ = smoke_output
    seen: set[str] = set()
    for path in out_dir.glob("*.json"):
        result = json.loads(path.read_text())
        for name in result.get("detected_entrypoints", []):
            seen.add(Path(name).name)
    assert EXPECTED_ENTRYPOINTS.issubset(seen), seen
