"""Diagnostic classification helpers."""

from __future__ import annotations

from detection.service import DetectionResult
from results.models import Diagnostic, SubmissionResult


def diagnose_submission(result: SubmissionResult, detection: DetectionResult) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    if detection.language == "java":
        diagnostics.extend(_java_discovery_diagnostics(detection))

    if result.build:
        diagnostics.extend(_java_compilation_diagnostics(result.build.stderr, result.build.timed_out, detection.language))

    if result.execution:
        diagnostics.extend(
            _java_runtime_diagnostics(
                result.execution.stderr,
                result.execution.exit_code,
                result.execution.timed_out,
                result.execution.input_used,
                detection.language,
            )
        )

    if detection.language == "java" and result.build and result.execution:
        if result.build.status == "success" and result.execution.status == "success":
            diagnostics.append(
                Diagnostic(
                    category="environment",
                    code="likely_ide_configuration_issue",
                    message=(
                        "SOURCE: PASS; COMPILATION: PASS; RUNTIME: PASS. "
                        "Submission runs successfully outside the IDE; any remaining IDE failure is likely project/module/classpath/run-configuration related."
                    ),
                    likely=True,
                )
            )

    if result.execution and result.execution.timed_out:
        diagnostics.append(
            Diagnostic(
                category="runtime",
                code="timeout",
                message="Execution timed out before completion.",
            )
        )

    return diagnostics


def _java_discovery_diagnostics(detection: DetectionResult) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    message = detection.message or ""

    if "No Java files found" in message:
        diagnostics.append(
            Diagnostic(
                category="discovery",
                code="no_java_files",
                message="No Java files found in submission.",
            )
        )

    if "Expected class/entrypoint not found" in message:
        diagnostics.append(
            Diagnostic(
                category="discovery",
                code="expected_class_not_found",
                message=message,
            )
        )

    if detection.requires_human_selection:
        diagnostics.append(
            Diagnostic(
                category="discovery",
                code="multiple_possible_entrypoints",
                message="Multiple Java main classes found; human selection required.",
            )
        )

    return diagnostics


def _java_compilation_diagnostics(stderr: str, timed_out: bool, language: str | None) -> list[Diagnostic]:
    if language != "java":
        return []

    if timed_out:
        return [Diagnostic(category="compilation", code="timeout", message="Compilation timed out.")]

    text = stderr or ""
    diagnostics: list[Diagnostic] = []
    lower = text.lower()

    if "cannot find symbol" in lower:
        diagnostics.append(
            Diagnostic(category="compilation", code="cannot_find_symbol", message="Compilation failed: cannot find symbol.")
        )
    if "is public, should be declared in a file named" in lower:
        diagnostics.append(
            Diagnostic(
                category="compilation",
                code="filename_public_class_mismatch",
                message="Compilation failed: public class name does not match filename.",
            )
        )
    if "package" in lower and "does not exist" in lower:
        diagnostics.append(
            Diagnostic(category="compilation", code="missing_dependency", message="Compilation failed: missing package/dependency.")
        )
    if "error:" in lower and not diagnostics:
        diagnostics.append(Diagnostic(category="compilation", code="syntax_error", message="Compilation failed with Java syntax error."))

    return diagnostics


def _java_runtime_diagnostics(
    stderr: str,
    exit_code: int | None,
    timed_out: bool,
    input_used: str | None,
    language: str | None,
) -> list[Diagnostic]:
    if language != "java" or timed_out:
        return []

    text = stderr or ""
    diagnostics: list[Diagnostic] = []

    patterns = {
        "ClassNotFoundException": "class_not_found_exception",
        "NoSuchMethodError": "no_such_method_error",
        "NoSuchElementException": "no_such_element_exception",
        "InputMismatchException": "input_mismatch_exception",
    }

    for token, code in patterns.items():
        if token in text:
            likely = token == "NoSuchElementException" and bool(input_used)
            message = f"Runtime failed with {token}."
            if likely:
                message += " Input may be insufficient for this interactive program."
            diagnostics.append(Diagnostic(category="runtime", code=code, message=message, likely=likely))

    if "Exception" in text and not diagnostics:
        diagnostics.append(
            Diagnostic(category="runtime", code="uncaught_exception", message="Runtime failed with uncaught exception.")
        )

    if exit_code not in (None, 0) and not diagnostics:
        diagnostics.append(
            Diagnostic(category="runtime", code="non_zero_exit", message=f"Program exited with non-zero exit code {exit_code}.")
        )

    return diagnostics
