"""Execution backend abstraction and local process runner."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Protocol

from results.models import CommandResult


class ExecutionBackend(Protocol):
    def run(
        self,
        command: list[str],
        cwd: Path,
        timeout_seconds: int,
        env: dict[str, str] | None = None,
    ) -> CommandResult: ...


class LocalProcessRunner:
    """Host-side runner; production should replace with sandboxed backend."""

    def run(
        self,
        command: list[str],
        cwd: Path,
        timeout_seconds: int,
        env: dict[str, str] | None = None,
    ) -> CommandResult:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        start = time.perf_counter()
        try:
            proc = subprocess.run(
                command,
                cwd=str(cwd),
                env=merged_env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            duration_ms = int((time.perf_counter() - start) * 1000)
            return CommandResult(
                status="success" if proc.returncode == 0 else "failed",
                command=" ".join(command),
                stdout=proc.stdout,
                stderr=proc.stderr,
                exit_code=proc.returncode,
                duration_ms=duration_ms,
                timed_out=False,
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return CommandResult(
                status="timeout",
                command=" ".join(command),
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
                exit_code=None,
                duration_ms=duration_ms,
                timed_out=True,
            )
