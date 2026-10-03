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
        stdin_input: str | None = None,
    ) -> CommandResult: ...


class LocalProcessRunner:
    """Host-side runner; production should replace with sandboxed backend."""

    def run(
        self,
        command: list[str],
        cwd: Path,
        timeout_seconds: int,
        env: dict[str, str] | None = None,
        stdin_input: str | None = None,
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
                input=stdin_input,
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
                input_used=stdin_input,
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout.decode("utf-8", "ignore") if exc.stdout else "")
            stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr.decode("utf-8", "ignore") if exc.stderr else "")
            return CommandResult(
                status="timeout",
                command=" ".join(command),
                stdout=stdout,
                stderr=stderr,
                exit_code=None,
                duration_ms=duration_ms,
                timed_out=True,
                input_used=stdin_input,
            )
        except FileNotFoundError as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return CommandResult(
                status="failed",
                command=" ".join(command),
                stdout="",
                stderr=str(exc),
                exit_code=127,
                duration_ms=duration_ms,
                timed_out=False,
                input_used=stdin_input,
            )
