# CscGrader

CscGrader is a language-agnostic command-line tool for CS instructors and TAs.
It detects student project language, runs build/compile steps when needed, executes submissions with timeouts, captures structured evidence, and leaves final grading to a human reviewer.

## Intended Use

CscGrader is for **evidence collection**, not automatic scoring.

Workflow:

1. Detection
2. Compilation / Build
3. Execution
4. Structured Results
5. Human Review

Human review is always required.

## Supported Languages (Initial)

- Java
- Python
- C
- C++
- JavaScript
- TypeScript
- Go
- Rust
- C#

## Architecture

Top-level modules:

- `/detection` - language and entrypoint detection
- `/compilation` - language adapter registry and build service
- `/execution` - execution backend and execution service
- `/results` - normalized result models and pipeline orchestration
- `/tests` - unit tests

Language-specific logic is isolated in adapters (`compilation/adapters.py`) so the core pipeline avoids language `if/elif` branching.

## Installation

```bash
python -m pip install -e .
```

## CLI Usage

```bash
cscgrader detect <submission>
cscgrader build <submission>
cscgrader run <submission>
cscgrader process <submission>
cscgrader process <submissions-directory>
```

Optional timeouts:

```bash
cscgrader build <submission> --timeout 30
cscgrader run <submission> --timeout 5
cscgrader process <path> --build-timeout 30 --run-timeout 5 --output-dir results
```

`process` runs:

`detect -> build -> execute -> save results`

If build fails, execution is skipped and the build failure is recorded.
For batch directories, each student is processed independently; one failure does not stop the rest.

## Result Format (JSON)

Example shape:

```json
{
  "submission": "StudentName",
  "language": "java",
  "entrypoint": "Main.java",
  "detection_status": "detected",
  "overall_status": "execution_success",
  "build": {
    "status": "success",
    "command": "javac Main.java",
    "stdout": "",
    "stderr": "",
    "exit_code": 0,
    "duration_ms": 100,
    "timed_out": false
  },
  "execution": {
    "status": "success",
    "command": "java Main",
    "stdout": "Hello",
    "stderr": "",
    "exit_code": 0,
    "duration_ms": 80,
    "timed_out": false
  },
  "requires_human_review": true
}
```

Statuses include:

- `detected`
- `unsupported`
- `build_success`
- `build_failed`
- `execution_success`
- `execution_failed`
- `timeout`
- `detection_failed`

## Examples

### Java submission

```bash
cscgrader process /path/to/StudentJava
```

Expected build command pattern:

```text
javac <all .java files>
```

Execution command pattern:

```text
java <detected-main-class>
```

### Python submission

```bash
cscgrader process /path/to/StudentPython
```

Build step is explicitly skipped.
Execution command pattern:

```text
python main.py
```

### Failed compilation

For a C submission with compile errors, CscGrader records compiler stderr and sets `overall_status` to `build_failed` without executing the program.

## Adding a New Language Adapter

1. Add an adapter implementing:
   - `requires_build()`
   - `build_command(submission_dir, entrypoint)`
   - `run_command(submission_dir, entrypoint)`
2. Register it in `AdapterRegistry`.
3. Extend detection in `detection/service.py`.
4. Add tests in `/tests` for detection and command generation.

## Testing

Run tests with:

```bash
pytest
```

## Security and Sandboxing Notes

Student submissions are untrusted code.

This initial implementation separates host orchestration from execution (`ExecutionBackend` interface), and includes timeout handling and explicit working-directory control.

For production use, replace local execution with isolated sandbox/container execution plus resource limits.

## Current Limitations

- Entrypoint detection uses practical heuristics and may not cover every project layout.
- Local runner executes on host machine (intended to be replaced by a sandbox backend for production).
- Build/run commands are representative defaults and may require adapter extension for course-specific frameworks.
