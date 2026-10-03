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


def test_detect_java_multiple_mains_requires_human_selection(tmp_path: Path) -> None:
    (tmp_path / "Alpha.java").write_text(
        "public class Alpha { public static void main(String[] args) {} }",
        encoding="utf-8",
    )
    (tmp_path / "Beta.java").write_text(
        "public class Beta { public static void main(String[] args) {} }",
        encoding="utf-8",
    )

    result = Detector().detect(tmp_path)

    assert result.status == Status.DETECTION_FAILED.value
    assert result.requires_human_selection is True
    assert sorted(result.entrypoints) == ["Alpha.java", "Beta.java"]


def test_detect_java_prefers_assignment_entrypoint(tmp_path: Path) -> None:
    (tmp_path / "BMI_CSC215_English_Student.java").write_text(
        "public class BMI_CSC215_English_Student { public static void main(String[] args) {} }",
        encoding="utf-8",
    )
    (tmp_path / "BMI_CSC215_Metric_Student.java").write_text(
        "public class BMI_CSC215_Metric_Student { public static void main(String[] args) {} }",
        encoding="utf-8",
    )

    result = Detector().detect(tmp_path, preferred_entrypoint="BMI_CSC215_Metric_Student.java")

    assert result.status == Status.DETECTED.value
    assert result.entrypoint == "BMI_CSC215_Metric_Student.java"


def test_detect_java_nested_submission_directory(tmp_path: Path) -> None:
    src = tmp_path / "src" / "nested"
    src.mkdir(parents=True)
    (src / "Main.java").write_text(
        "public class Main { public static void main(String[] args) {} }",
        encoding="utf-8",
    )

    result = Detector().detect(tmp_path)

    assert result.status == Status.DETECTED.value
    assert result.entrypoint == "src/nested/Main.java"
