"""Explicit tests for how the {student} token is derived."""

from pathlib import Path

from assignment.profiles import (
    AssignmentProfile,
    AssignmentProfileLoader,
    infer_student_token,
)

FIXTURE = Path(__file__).parent / "fixtures" / "dummy_submission"
PROFILE = Path(__file__).parent / "fixtures" / "dummy_submission_assignment.json"


def test_load_returns_none_for_none_path():
    assert AssignmentProfileLoader.load(None) is None


def test_profile_student_identifier_takes_precedence():
    profile = AssignmentProfileLoader.load(PROFILE)
    assert profile is not None
    assert profile.resolve_student(FIXTURE) == "DummyStudent"


def test_resolver_falls_back_to_filename_convention():
    profile = AssignmentProfile(
        name="No Explicit Identifier",
        parts=[],
        student_identifier=None,
    )
    assert profile.resolve_student(FIXTURE) == "DummyStudent"


def test_resolver_falls_back_to_directory_name(tmp_path):
    profile = AssignmentProfile(
        name="No Explicit Identifier",
        parts=[],
        student_identifier=None,
    )
    d = tmp_path / "StudentDir"
    d.mkdir()
    assert profile.resolve_student(d) == infer_student_token("StudentDir")


def test_resolve_for_submission_replaces_student_token():
    profile = AssignmentProfileLoader.load(PROFILE)
    resolved = AssignmentProfileLoader.resolve_for_submission(profile, FIXTURE)
    assert resolved.student == "DummyStudent"
    names = sorted(p.entrypoint for p in resolved.parts)
    assert names == [
        "BMI_CSC215_English_DummyStudent.java",
        "BMI_CSC215_MASTER_DummyStudent.java",
        "BMI_CSC215_Metric_DummyStudent.java",
    ]
    for part in resolved.parts:
        assert (FIXTURE / part.entrypoint).exists()


def test_legacy_pipeline_profile_still_resolves():
    """Mirror of tests/test_pipeline.py::test_assignment_profile_master_english_metric."""
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        sub = root / "BenjaminSlye"
        sub.mkdir()
        for suffix in ("English", "Metric", "MASTER"):
            (sub / f"BMI_CSC215_{suffix}_BenjaminSlye.java").write_text(
                f"public class BMI_CSC215_{suffix}_BenjaminSlye {{ public static void main(String[] a) {{}} }}",
                encoding="utf-8",
            )
        profile_path = root / "csc215-assignment-03.json"
        profile_path.write_text(
            json.dumps({
                "name": "CSC 215 Assignment 03",
                "parts": [
                    {"name": "Part A", "entrypoint": "BMI_CSC215_English_{student}.java"},
                    {"name": "Part B", "entrypoint": "BMI_CSC215_Metric_{student}.java"},
                    {"name": "Part C", "entrypoint": "BMI_CSC215_MASTER_{student}.java",
                     "dependencies": [
                         "BMI_CSC215_English_{student}.java",
                         "BMI_CSC215_Metric_{student}.java",
                     ]},
                ],
            }),
            encoding="utf-8",
        )
        profile = AssignmentProfileLoader.load(profile_path)
        resolved = AssignmentProfileLoader.resolve_for_submission(profile, sub)
        assert resolved.student == "BenjaminSlye"
        for part in resolved.parts:
            assert (sub / part.entrypoint).exists()
