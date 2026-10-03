"""Normalized, serializable result models for CscGrader."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Status(str, Enum):
    """Pipeline statuses for submission processing."""

    DETECTED = "detected"
    UNSUPPORTED = "unsupported"
    BUILD_SUCCESS = "build_success"
    BUILD_FAILED = "build_failed"
    EXECUTION_SUCCESS = "execution_success"
    EXECUTION_FAILED = "execution_failed"
    TIMEOUT = "timeout"
    DETECTION_FAILED = "detection_failed"


@dataclass
class Diagnostic:
    """Human-focused diagnostic evidence."""

    category: str
    code: str
    message: str
    likely: bool = False


@dataclass
class CommandResult:
    """Captured output for a command execution."""

    status: str
    command: str
    stdout: str
    stderr: str
    exit_code: int | None
    duration_ms: int
    timed_out: bool = False
    input_used: str | None = None


@dataclass
class SubmissionResult:
    """Language-neutral submission processing result."""

    submission: str
    language: str | None
    entrypoint: str | None
    detection_status: str
    overall_status: str
    assignment: str | None = None
    part: str | None = None
    detected_entrypoints: list[str] = field(default_factory=list)
    build: CommandResult | None = None
    execution: CommandResult | None = None
    diagnostics: list[Diagnostic] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    requires_human_review: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, **kwargs: Any) -> str:
        import json

        return json.dumps(self.to_dict(), **kwargs)
