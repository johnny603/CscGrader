"""Project language and entrypoint detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from results.models import Status


LANG_EXTENSIONS = {
    "java": {".java"},
    "python": {".py"},
    "c": {".c"},
    "cpp": {".cpp", ".cc", ".cxx"},
    "javascript": {".js"},
    "typescript": {".ts"},
    "go": {".go"},
    "rust": {".rs"},
    "csharp": {".cs"},
}

MAIN_METHOD_RE = re.compile(r"public\s+static\s+void\s+main\s*\(")
CLASS_RE = re.compile(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)")


@dataclass
class DetectionResult:
    """Structured result for submission detection."""

    status: str
    language: str | None = None
    project_type: str | None = None
    entrypoint: str | None = None
    entrypoints: list[str] = field(default_factory=list)
    message: str | None = None
    requires_human_selection: bool = False
    discovered_files: list[str] = field(default_factory=list)


class Detector:
    """Detect language, project type, and likely entrypoint."""

    def detect(self, submission_dir: str | Path, preferred_entrypoint: str | None = None) -> DetectionResult:
        root = Path(submission_dir).resolve()
        if not root.exists() or not root.is_dir():
            return DetectionResult(
                status=Status.DETECTION_FAILED.value,
                message="Submission directory does not exist.",
            )

        language = self._detect_language(root)
        if language is None:
            return DetectionResult(
                status=Status.UNSUPPORTED.value,
                message="Unable to confidently detect supported language.",
            )

        if language == "java":
            return self._detect_java(root, preferred_entrypoint=preferred_entrypoint)

        entrypoint = self._detect_entrypoint(root, language)
        if entrypoint is None:
            return DetectionResult(
                status=Status.DETECTION_FAILED.value,
                language=language,
                project_type=language,
                message="Language detected but entrypoint could not be determined confidently.",
            )

        return DetectionResult(
            status=Status.DETECTED.value,
            language=language,
            project_type=language,
            entrypoint=entrypoint,
            entrypoints=[entrypoint],
            message="Detection successful.",
        )

    def _detect_java(self, root: Path, preferred_entrypoint: str | None = None) -> DetectionResult:
        java_files = sorted(
            str(path.relative_to(root)) for path in root.rglob("*.java") if path.is_file() and not self._is_hidden(path)
        )
        if not java_files:
            return DetectionResult(
                status=Status.DETECTION_FAILED.value,
                language="java",
                project_type="java",
                message="No Java files found.",
                discovered_files=[],
            )

        entrypoint_candidates = self._discover_java_entrypoints(root, java_files)
        if not entrypoint_candidates:
            return DetectionResult(
                status=Status.DETECTION_FAILED.value,
                language="java",
                project_type="java",
                message="Java files found but no class with public static void main was detected.",
                discovered_files=java_files,
            )

        if preferred_entrypoint:
            matched = self._match_preferred_entrypoint(preferred_entrypoint, entrypoint_candidates)
            if matched:
                return DetectionResult(
                    status=Status.DETECTED.value,
                    language="java",
                    project_type="java",
                    entrypoint=matched,
                    entrypoints=entrypoint_candidates,
                    discovered_files=java_files,
                    message="Detection successful with assignment-preferred entrypoint.",
                )
            return DetectionResult(
                status=Status.DETECTION_FAILED.value,
                language="java",
                project_type="java",
                entrypoints=entrypoint_candidates,
                discovered_files=java_files,
                message=f"Expected class/entrypoint not found: {preferred_entrypoint}",
            )

        if len(entrypoint_candidates) == 1:
            selected = entrypoint_candidates[0]
            return DetectionResult(
                status=Status.DETECTED.value,
                language="java",
                project_type="java",
                entrypoint=selected,
                entrypoints=entrypoint_candidates,
                discovered_files=java_files,
                message="Detection successful.",
            )

        heuristic_selected = self._select_java_entrypoint_heuristically(entrypoint_candidates)
        if heuristic_selected:
            return DetectionResult(
                status=Status.DETECTED.value,
                language="java",
                project_type="java",
                entrypoint=heuristic_selected,
                entrypoints=entrypoint_candidates,
                discovered_files=java_files,
                message="Multiple Java entrypoints found; selected using strong heuristic (master/main naming).",
            )

        return DetectionResult(
            status=Status.DETECTION_FAILED.value,
            language="java",
            project_type="java",
            entrypoints=entrypoint_candidates,
            discovered_files=java_files,
            requires_human_selection=True,
            message="Multiple Java entrypoints found; human selection required.",
        )

    @staticmethod
    def _discover_java_entrypoints(root: Path, java_files: list[str]) -> list[str]:
        candidates: list[str] = []
        for rel_path in java_files:
            path = root / rel_path
            text = Detector._safe_read(path)
            if MAIN_METHOD_RE.search(text):
                candidates.append(rel_path)
        return sorted(candidates)

    @staticmethod
    def _match_preferred_entrypoint(preferred: str, entrypoints: list[str]) -> str | None:
        normalized = preferred.replace("\\", "/")
        preferred_class = Path(normalized).stem
        for candidate in entrypoints:
            if candidate == normalized:
                return candidate
            if Path(candidate).name == normalized:
                return candidate
            if Path(candidate).stem == preferred_class:
                return candidate
        return None

    @staticmethod
    def _select_java_entrypoint_heuristically(entrypoints: list[str]) -> str | None:
        ranked: list[tuple[int, str]] = []
        for entrypoint in entrypoints:
            name = Path(entrypoint).stem.lower()
            score = 0
            if "master" in name:
                score += 4
            if name == "main":
                score += 3
            if name.endswith("main"):
                score += 2
            if "test" in name:
                score -= 4
            ranked.append((score, entrypoint))

        ranked.sort(reverse=True)
        if not ranked or ranked[0][0] <= 0:
            return None
        if len(ranked) > 1 and ranked[0][0] == ranked[1][0]:
            return None
        return ranked[0][1]

    def _detect_language(self, root: Path) -> str | None:
        metadata_map = {
            "java": ["pom.xml", "build.gradle", "settings.gradle"],
            "javascript": ["package.json"],
            "typescript": ["tsconfig.json"],
            "go": ["go.mod"],
            "rust": ["Cargo.toml"],
        }
        for language, markers in metadata_map.items():
            if any((root / marker).exists() for marker in markers):
                return language

        if list(root.glob("*.csproj")) or list(root.glob("*.sln")):
            return "csharp"

        counts = {k: 0 for k in LANG_EXTENSIONS}
        for path in root.rglob("*"):
            if path.is_file() and not self._is_hidden(path):
                for language, exts in LANG_EXTENSIONS.items():
                    if path.suffix.lower() in exts:
                        counts[language] += 1

        best_language, best_count = max(counts.items(), key=lambda item: item[1])
        if best_count == 0:
            return None

        if list(counts.values()).count(best_count) > 1:
            return None

        return best_language

    def _detect_entrypoint(self, root: Path, language: str) -> str | None:
        if language == "python":
            for name in ("main.py", "app.py", "__main__.py"):
                p = root / name
                if p.exists():
                    return name
            candidates = sorted(root.glob("*.py"))
            return str(candidates[0].name) if candidates else None

        if language == "c":
            for name in ("main.c",):
                p = root / name
                if p.exists():
                    return name
            candidates = sorted(root.glob("*.c"))
            return candidates[0].name if candidates else None

        if language == "cpp":
            for name in ("main.cpp", "main.cc", "main.cxx"):
                p = root / name
                if p.exists():
                    return name
            candidates: list[Path] = []
            for ext in ("*.cpp", "*.cc", "*.cxx"):
                candidates.extend(root.glob(ext))
            candidates = sorted(candidates)
            return candidates[0].name if candidates else None

        if language == "javascript":
            for name in ("index.js", "main.js", "app.js"):
                p = root / name
                if p.exists():
                    return name
            candidates = sorted(root.glob("*.js"))
            return candidates[0].name if candidates else None

        if language == "typescript":
            for name in ("index.ts", "main.ts", "app.ts"):
                p = root / name
                if p.exists():
                    return name
            candidates = sorted(root.glob("*.ts"))
            return candidates[0].name if candidates else None

        if language == "go":
            for candidate in root.rglob("*.go"):
                text = self._safe_read(candidate)
                if "package main" in text and "func main(" in text:
                    return str(candidate.relative_to(root))
            return None

        if language == "rust":
            main_rs = root / "src" / "main.rs"
            if main_rs.exists():
                return str(main_rs.relative_to(root))
            return None

        if language == "csharp":
            for candidate in root.rglob("*.cs"):
                text = self._safe_read(candidate)
                if "static void Main(" in text or "static async Task Main(" in text:
                    return str(candidate.relative_to(root))
            return None

        return None

    @staticmethod
    def _safe_read(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ""

    @staticmethod
    def _is_hidden(path: Path) -> bool:
        return any(part.startswith(".") for part in path.parts)
