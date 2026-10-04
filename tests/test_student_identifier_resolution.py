"""Explicit tests for how the {student} token is derived."""

from pathlib import Path

from assignment.profiles import (
    AssignmentProfile,
    AssignmentProfileLoader,
    infer_student_token,
)

FIXTURE = Path(__file__).parent / "fixtures" / "dummy_submission"
PROFILE = Path(__file__).parent / "fixtures" / "dummy_submission_assignment.json"


def test_profile_student_identifier_takes_precedence():
    profile = AssignmentProfileLoader.load(PROFILE)
    assert profile.resolve_student(FIXTURE) == "DummyStudent"


def test_resolver_falls_back_to_filename_convention():
    profile = AssignmentProfile(
        name="No Explicit Identifier",
        parts=[],
        student_identifier=None,
    )
    assert profile.resolve_student(FIXTURE) == "DummyStudent"


def test_resolver_falls_back_to_directory_name(tmp_path):
    # Empty submission dir with no Java files -> falls back to dir name via
    # infer_student_token, which preserves the legacy behavior.
    profile = AssignmentProfile(
        name="No Explicit Identifier",
        parts=[],
        student_identifier=None,
    )
    d = tmp_path / "StudentDir"
    d.mkdir()
    assert profile.resolve_student(d) == infer_student_token("StudentDir")


def test_entrypoint_template_resolves_to_real_file():
    profile = AssignmentProfileLoader.load(PROFILE)
    student = profile.resolve_student(FIXTURE)
    for part in profile.parts:
        resolved = FIXTURE / part.entrypoint.replace("{student}", student)
        assert resolved.exists(), f"missing {resolved}"


def test_loader_resolves_all_parts():
    profile = AssignmentProfileLoader.load(PROFILE)
    resolved = AssignmentProfileLoader.resolve(profile, FIXTURE)
    assert resolved.student == "DummyStudent"
    names = sorted(p.entrypoint for p in resolved.parts)
    assert names == [
        "BMI_CSC215_English_DummyStudent.java",
        "BMI_CSC215_MASTER_DummyStudent.java",
        "BMI_CSC215_Metric_DummyStudent.java",
    ]
    for part in resolved.parts:
        assert (FIXTURE / part.entrypoint).exists()
