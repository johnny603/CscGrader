from pathlib import Path

from detection.service import Detector
from results.models import Status


def test_detect_python_and_entrypoint(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hi')", encoding="utf-8")

    result = Detector().detect(tmp_path)

    assert result.status == Status.DETECTED.value
    assert result.language == "python"
    assert result.entrypoint == "main.py"


def test_detect_unsupported_language(tmp_path: Path) -> None:
    (tmp_path / "README.txt").write_text("no code", encoding="utf-8")

    result = Detector().detect(tmp_path)

    assert result.status == Status.UNSUPPORTED.value


def test_detect_detection_failed_when_no_entrypoint(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module sample", encoding="utf-8")
    (tmp_path / "util.go").write_text("package util", encoding="utf-8")

    result = Detector().detect(tmp_path)

    assert result.status == Status.DETECTION_FAILED.value
    assert result.language == "go"
