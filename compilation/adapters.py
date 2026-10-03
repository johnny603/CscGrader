"""Language adapter abstractions and registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class LanguageAdapter(Protocol):
    language: str

    def requires_build(self) -> bool: ...

    def build_command(self, submission_dir: Path, entrypoint: str) -> list[str] | None: ...

    def run_command(self, submission_dir: Path, entrypoint: str) -> list[str]: ...


@dataclass
class BaseAdapter:
    language: str

    def requires_build(self) -> bool:
        return True

    def build_command(self, submission_dir: Path, entrypoint: str) -> list[str] | None:
        raise NotImplementedError

    def run_command(self, submission_dir: Path, entrypoint: str) -> list[str]:
        raise NotImplementedError


class JavaAdapter(BaseAdapter):
    def __init__(self) -> None:
        super().__init__("java")

    def build_command(self, submission_dir: Path, entrypoint: str) -> list[str] | None:
        java_files = [str(p.relative_to(submission_dir)) for p in submission_dir.rglob("*.java")]
        return ["javac", *sorted(java_files)] if java_files else None

    def run_command(self, submission_dir: Path, entrypoint: str) -> list[str]:
        class_name = entrypoint.removesuffix(".java").replace("/", ".").replace("\\", ".")
        return ["java", class_name]


class PythonAdapter(BaseAdapter):
    def __init__(self) -> None:
        super().__init__("python")

    def requires_build(self) -> bool:
        return False

    def build_command(self, submission_dir: Path, entrypoint: str) -> list[str] | None:
        return None

    def run_command(self, submission_dir: Path, entrypoint: str) -> list[str]:
        return ["python", entrypoint]


class CAdapter(BaseAdapter):
    def __init__(self) -> None:
        super().__init__("c")

    def build_command(self, submission_dir: Path, entrypoint: str) -> list[str] | None:
        c_files = [str(p.relative_to(submission_dir)) for p in submission_dir.glob("*.c")]
        return ["gcc", *sorted(c_files), "-o", "program"] if c_files else None

    def run_command(self, submission_dir: Path, entrypoint: str) -> list[str]:
        return ["./program"]


class CppAdapter(BaseAdapter):
    def __init__(self) -> None:
        super().__init__("cpp")

    def build_command(self, submission_dir: Path, entrypoint: str) -> list[str] | None:
        files: list[str] = []
        for ext in ("*.cpp", "*.cc", "*.cxx"):
            files.extend(str(p.relative_to(submission_dir)) for p in submission_dir.glob(ext))
        return ["g++", *sorted(files), "-o", "program"] if files else None

    def run_command(self, submission_dir: Path, entrypoint: str) -> list[str]:
        return ["./program"]


class JavaScriptAdapter(BaseAdapter):
    def __init__(self) -> None:
        super().__init__("javascript")

    def requires_build(self) -> bool:
        return False

    def build_command(self, submission_dir: Path, entrypoint: str) -> list[str] | None:
        return None

    def run_command(self, submission_dir: Path, entrypoint: str) -> list[str]:
        return ["node", entrypoint]


class TypeScriptAdapter(BaseAdapter):
    def __init__(self) -> None:
        super().__init__("typescript")

    def build_command(self, submission_dir: Path, entrypoint: str) -> list[str] | None:
        return ["tsc"]

    def run_command(self, submission_dir: Path, entrypoint: str) -> list[str]:
        return ["node", entrypoint.removesuffix(".ts") + ".js"]


class GoAdapter(BaseAdapter):
    def __init__(self) -> None:
        super().__init__("go")

    def build_command(self, submission_dir: Path, entrypoint: str) -> list[str] | None:
        return ["go", "build", "./..."]

    def run_command(self, submission_dir: Path, entrypoint: str) -> list[str]:
        return ["go", "run", "."]


class RustAdapter(BaseAdapter):
    def __init__(self) -> None:
        super().__init__("rust")

    def build_command(self, submission_dir: Path, entrypoint: str) -> list[str] | None:
        return ["cargo", "build"]

    def run_command(self, submission_dir: Path, entrypoint: str) -> list[str]:
        return ["cargo", "run", "--quiet"]


class CSharpAdapter(BaseAdapter):
    def __init__(self) -> None:
        super().__init__("csharp")

    def build_command(self, submission_dir: Path, entrypoint: str) -> list[str] | None:
        sln = sorted(submission_dir.glob("*.sln"))
        if sln:
            return ["dotnet", "build", sln[0].name]
        csproj = sorted(submission_dir.glob("*.csproj"))
        if csproj:
            return ["dotnet", "build", csproj[0].name]
        return ["dotnet", "build"]

    def run_command(self, submission_dir: Path, entrypoint: str) -> list[str]:
        csproj = sorted(submission_dir.glob("*.csproj"))
        if csproj:
            return ["dotnet", "run", "--project", csproj[0].name]
        return ["dotnet", "run"]


class AdapterRegistry:
    """Registry that resolves language adapters without if/elif in pipeline."""

    def __init__(self) -> None:
        adapters = [
            JavaAdapter(),
            PythonAdapter(),
            CAdapter(),
            CppAdapter(),
            JavaScriptAdapter(),
            TypeScriptAdapter(),
            GoAdapter(),
            RustAdapter(),
            CSharpAdapter(),
        ]
        self._adapters = {adapter.language: adapter for adapter in adapters}

    def get(self, language: str) -> LanguageAdapter | None:
        return self._adapters.get(language)
