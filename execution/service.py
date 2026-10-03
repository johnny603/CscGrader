"""Execution orchestration for built submissions."""

from __future__ import annotations

from pathlib import Path

from compilation.adapters import LanguageAdapter
from execution.runner import ExecutionBackend
from results.models import CommandResult


class ExecutionService:
    """Executes a submission via adapter-generated command."""

    def __init__(self, runner: ExecutionBackend) -> None:
        self.runner = runner

    def execute(
        self,
        adapter: LanguageAdapter,
        submission_dir: Path,
        entrypoint: str,
        timeout_seconds: int,
    ) -> CommandResult:
        command = adapter.run_command(submission_dir, entrypoint)
        return self.runner.run(command, submission_dir, timeout_seconds)
