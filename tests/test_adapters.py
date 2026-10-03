from pathlib import Path

from compilation.adapters import JavaAdapter


def test_java_build_command_includes_all_java_files(tmp_path: Path) -> None:
    (tmp_path / "Main.java").write_text("class Main{}", encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    (src / "Helper.java").write_text("class Helper{}", encoding="utf-8")

    command = JavaAdapter().build_command(tmp_path, "Main.java")

    assert command is not None
    assert command[0] == "javac"
    assert "Main.java" in command
    assert "src/Helper.java" in command


def test_java_run_command_uses_entrypoint_class_name() -> None:
    cmd = JavaAdapter().run_command(Path("."), "src/Main.java")
    assert cmd == ["java", "src.Main"]
