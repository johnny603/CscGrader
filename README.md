# CscGrader

CscGrader is a language-agnostic evidence-collection tool for CS instructors and TAs.
It detects student submissions, compiles/builds them when required, executes them with timeout controls, captures structured results, and prepares output for **human review**.

CscGrader does **not** auto-grade or assign scores.

## Workflow

Student Submission → Detection → Compilation/Build → Execution → Results/Evidence → Human Review

## Installation

```bash
python -m pip install -e .
```

## CLI

```bash
cscgrader detect <submission> [--entrypoint <entrypoint-or-class>]
cscgrader build <submission> [--entrypoint <entrypoint-or-class>] [--timeout 30]
cscgrader run <submission> [--entrypoint <entrypoint-or-class>] [--timeout 5] [--input test-input.txt]
cscgrader process <submission|submissions-directory> [--assignment profile.json] [--input test-input.txt]
cscgrader batch <submissions-directory> [--assignment profile.json] [--input test-input.txt]
```

`process`/`batch` always save machine-readable JSON evidence per submission/part.

## Assignment Profiles (Reusable)

Assignment profiles are JSON and are not hard-coded to a specific course.

```json
{
  "name": "CSC 215 Assignment 03",
  "parts": [
    {"name": "Part A", "entrypoint": "BMI_CSC215_English_{student}.java"},
    {"name": "Part B", "entrypoint": "BMI_CSC215_Metric_{student}.java"},
    {
      "name": "Part C",
      "entrypoint": "BMI_CSC215_MASTER_{student}.java",
      "dependencies": [
        "BMI_CSC215_English_{student}.java",
        "BMI_CSC215_Metric_{student}.java"
      ]
    }
  ]
}
```

Run:

```bash
cscgrader process ./KeshviDobariya-Assignment-03 --assignment ./csc215-assignment-03.json
```

## Java Improvements

- Discovers all Java files recursively.
- Detects all classes/files containing `public static void main`.
- Reports all candidate entrypoints.
- Uses assignment-configured entrypoint when provided.
- Avoids silently choosing arbitrary entrypoints when multiple candidates exist.
- Compiles multi-file Java submissions using all discovered `.java` files.
- Emits diagnostics for common discovery/build/runtime failure categories.

## Deterministic stdin

Provide test input for interactive programs:

```bash
cscgrader run ./StudentSubmission --input test-input.txt
```

Captured evidence includes input used, stdout/stderr, exit code, duration, and timeout.

## Human-readable summary + JSON evidence

`process`/`batch` print concise per-student/part summaries and diagnostics (for TA workflow), while JSON files retain full evidence for later tooling.

## Diagnostics (examples)

Discovery:
- no Java files found
- multiple possible entrypoints (human selection required)
- expected class/entrypoint not found

Compilation:
- syntax error
- cannot find symbol
- missing dependency/package
- public class/filename mismatch

Runtime:
- ClassNotFoundException
- NoSuchMethodError
- NoSuchElementException (likely insufficient stdin when input is supplied)
- InputMismatchException
- uncaught exception
- non-zero exit code
- timeout

Environment/IDE signal:
- when source compiles/runs successfully in terminal, CscGrader reports that remaining failures are likely IDE project/classpath/run-configuration issues.

## Architecture

- `detection/` for language and entrypoint discovery
- `compilation/` for language adapters and build commands
- `execution/` for execution backend abstraction and local runner
- `results/` for normalized models, diagnostics, and pipeline orchestration
- `assignment/` for reusable assignment profiles

Language behavior remains modular through adapters/registry.

## Security / limitations

Student code is untrusted. Current local runner is for development only.
Production deployments should use an isolated sandbox/container backend with strict resource limits.
Timeout enforcement is built in and should remain enabled.

## Testing

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

### Built-in dummy submission smoke test

The repository includes a first-class Java fixture at:

- `tests/fixtures/dummy_submission/`
- `tests/fixtures/dummy_submission_assignment.json`

Quick smoke workflow after clone/install:

```bash
cscgrader process tests/fixtures/dummy_submission \
  --assignment tests/fixtures/dummy_submission_assignment.json \
  --output-dir /tmp/cscgrader-smoke-results
```

This validates assignment-aware Java discovery, multi-file compilation, execution with stdin, concise summary output, and JSON evidence generation before processing real student submissions.
