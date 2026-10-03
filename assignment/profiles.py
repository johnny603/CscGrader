"""Assignment profile configuration and resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re


@dataclass
class AssignmentPart:
    name: str
    entrypoint: str
    dependencies: list[str]
    input_file: str | None = None
    input_text: str | None = None
    run_command: list[str] | None = None


@dataclass
class AssignmentProfile:
    name: str
    parts: list[AssignmentPart]

    @staticmethod
    def from_dict(data: dict) -> "AssignmentProfile":
        parts = [
            AssignmentPart(
                name=part["name"],
                entrypoint=part["entrypoint"],
                dependencies=part.get("dependencies", []),
                input_file=part.get("input_file"),
                input_text=part.get("input_text"),
                run_command=part.get("run_command"),
            )
            for part in data.get("parts", [])
        ]
        return AssignmentProfile(name=data["name"], parts=parts)


@dataclass
class ResolvedAssignmentPart:
    name: str
    entrypoint: str
    dependencies: list[str]
    input_text: str | None
    run_command: list[str] | None


@dataclass
class ResolvedAssignment:
    name: str
    parts: list[ResolvedAssignmentPart]


class AssignmentProfileLoader:
    """Loads assignment profiles from JSON files."""

    def load(self, assignment: str | None) -> AssignmentProfile | None:
        if not assignment:
            return None

        candidate = Path(assignment)
        if candidate.exists():
            return self._read_profile(candidate)

        roots = [
            Path.cwd() / "assignment_profiles" / f"{assignment}.json",
            Path.cwd() / ".cscgrader" / "assignments" / f"{assignment}.json",
        ]
        for root in roots:
            if root.exists():
                return self._read_profile(root)

        raise FileNotFoundError(f"Assignment profile not found: {assignment}")

    @staticmethod
    def resolve_for_submission(profile: AssignmentProfile, submission_dir: Path) -> ResolvedAssignment:
        student = infer_student_token(submission_dir.name)
        parts: list[ResolvedAssignmentPart] = []

        for part in profile.parts:
            dependencies = [dep.replace("{student}", student) for dep in part.dependencies]
            entrypoint = part.entrypoint.replace("{student}", student)

            input_text = part.input_text
            if part.input_file:
                input_path = submission_dir / part.input_file
                if input_path.exists():
                    input_text = input_path.read_text(encoding="utf-8")

            parts.append(
                ResolvedAssignmentPart(
                    name=part.name,
                    entrypoint=entrypoint,
                    dependencies=dependencies,
                    input_text=input_text,
                    run_command=part.run_command,
                )
            )

        return ResolvedAssignment(name=profile.name, parts=parts)

    @staticmethod
    def _read_profile(path: Path) -> AssignmentProfile:
        data = json.loads(path.read_text(encoding="utf-8"))
        return AssignmentProfile.from_dict(data)


def infer_student_token(submission_name: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]", "", submission_name)
    return token or submission_name
