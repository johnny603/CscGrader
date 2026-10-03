"""Build orchestration for detected submissions."""

from __future__ import annotations

from pathlib import Path

from compilation.adapters import LanguageAdapter
from execution.runner import ExecutionBackend
from results.models import CommandResult


class BuildService:
    """Builds a submission using its language adapter."""

    def __init__(self, runner: ExecutionBackend) -> None:
        self.runner = runner

    def build(
        self,
        adapter: LanguageAdapter,
        submission_dir: Path,
        entrypoint: str,
        timeout_seconds: int,
    ) -> CommandResult:
        command = adapter.build_command(submission_dir, entrypoint)
        if not adapter.requires_build() or command is None:
            return CommandResult(
                status="skipped",
                command="",
                stdout="",
                stderr="",
                exit_code=0,
                duration_ms=0,
                timed_out=False,
            )
        return self.runner.run(command, submission_dir, timeout_seconds)
