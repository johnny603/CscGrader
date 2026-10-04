"""Assignment profile models and loader."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AssignmentPart:
    name: str
    entrypoint: str
    dependencies: list[str] = field(default_factory=list)
    timeout_seconds: int | None = None
    input_text: str | None = None       # ADDED
    run_command: str | None = None      # ADDED


@dataclass
class AssignmentProfile:
    name: str
    parts: list[AssignmentPart]
    student_identifier: str | None = None  # ADDED

    # ADDED
    def resolve_student(self, submission_path: str | Path) -> str:
        """Resolve the {student} token used in entrypoint templates.

        Precedence:
          1. profile.student_identifier (explicit)
          2. inferred from a BMI_CSC215_*_<StudentId>.java file
          3. submission directory name (legacy)
        """
        if self.student_identifier:
            return self.student_identifier

        root = Path(submission_path)
        for name in sorted(p.name for p in root.glob("*.java")):
            if name.startswith("BMI_CSC215_") and name.endswith(".java"):
                stem = name[len("BMI_CSC215_"):-len(".java")]  # English_DummyStudent
                if "_" in stem:
                    return stem.split("_", 1)[1]

        return infer_student_token(root.name)


@dataclass
class ResolvedAssignmentPart:
    name: str
    entrypoint: str
    dependencies: list[str] = field(default_factory=list)
    input_text: str | None = None       # ADDED: pipeline.py reads part.input_text
    run_command: str | None = None      # ADDED: pipeline.py reads part.run_command


@dataclass
class ResolvedAssignment:
    name: str
    parts: list[ResolvedAssignmentPart]
    student: str | None = None  # ADDED


class AssignmentProfileLoader:
    @staticmethod
    def load(path: str | Path | None) -> AssignmentProfile | None:
        if path is None:                            # ADDED: tolerate assignment=None
            return None                             # ADDED
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        parts = [
            AssignmentPart(
                name=p["name"],
                entrypoint=p["entrypoint"],
                dependencies=list(p.get("dependencies", [])),
                timeout_seconds=p.get("timeout_seconds"),
                input_text=p.get("input_text"),     # ADDED
                run_command=p.get("run_command"),   # ADDED
            )
            for p in data["parts"]
        ]
        return AssignmentProfile(
            name=data["name"],
            parts=parts,
            student_identifier=data.get("student_identifier"),  # ADDED
        )

    # ADDED: renamed from `resolve` to match results/pipeline.py:164
    @staticmethod
    def resolve_for_submission(
        profile: AssignmentProfile,
        submission_path: str | Path,
    ) -> ResolvedAssignment:
        submission_path = Path(submission_path)
        student = profile.resolve_student(submission_path)
        resolved_parts: list[ResolvedAssignmentPart] = []
        for part in profile.parts:
            entrypoint = part.entrypoint.replace("{student}", student)
            dependencies = [
                dep.replace("{student}", student) for dep in part.dependencies
            ]
            resolved_parts.append(
                ResolvedAssignmentPart(
                    name=part.name,
                    entrypoint=entrypoint,
                    dependencies=dependencies,
                    input_text=part.input_text,         # ADDED
                    run_command=part.run_command,       # ADDED
                )
            )
        return ResolvedAssignment(
            name=profile.name,
            parts=resolved_parts,
            student=student,
        )


def infer_student_token(submission_name: str) -> str:
    """Legacy fallback: derive a student token from a submission name."""
    return submission_name
