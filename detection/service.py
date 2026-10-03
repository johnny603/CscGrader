"""Project language and entrypoint detection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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


@dataclass
class DetectionResult:
    """Structured result for submission detection."""

    status: str
    language: str | None = None
    project_type: str | None = None
    entrypoint: str | None = None
    message: str | None = None


class Detector:
    """Detect language, project type, and likely entrypoint."""

    def detect(self, submission_dir: str | Path) -> DetectionResult:
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
            message="Detection successful.",
        )

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
        if language == "java":
            candidates = list(root.rglob("*.java"))
            for candidate in candidates:
                text = self._safe_read(candidate)
                if "public static void main" in text:
                    return str(candidate.relative_to(root))
            return None

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
