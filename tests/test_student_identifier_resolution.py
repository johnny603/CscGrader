from pathlib import Path
from assignment.profiles import load_profile, resolve_student_identifier  # adjust to real API

FIXTURE = Path(__file__).parent / "fixtures" / "dummy_submission"
PROFILE = Path(__file__).parent / "fixtures" / "dummy_submission_assignment.json"

def test_profile_identifier_takes_precedence():
    profile = load_profile(PROFILE)
    assert resolve_student_identifier(profile, FIXTURE) == "DummyStudent"

def test_entrypoint_template_resolves_to_real_file():
    profile = load_profile(PROFILE)
    student = resolve_student_identifier(profile, FIXTURE)
    for part in profile["parts"]:
        resolved = FIXTURE / part["entrypoint"].format(student=student)
        assert resolved.exists(), f"missing {resolved}"
