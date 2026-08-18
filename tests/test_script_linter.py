import importlib.util
from pathlib import Path


TOOLS = (
    Path(__file__).parents[1]
    / "claude"
    / "series-studio"
    / "template"
    / "tools"
)


def load_linter():
    spec = importlib.util.spec_from_file_location("lint_script", TOOLS / "lint_script.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_narration_ignores_screen_directions():
    linter = load_linter()
    markdown = """## 01 Opening

**【畫面】**
Do not narrate this.

**【旁白】**
只留下這段旁白。

---
"""

    assert linter.parse_narration(markdown) == [(7, "只留下這段旁白。")]


def test_lint_detects_voice_hazards():
    linter = load_linter()

    errors, _warnings, _ear = linter.lint(
        [(1, "我們跑跑看——留言告訴我結果。")],
        {},
    )

    rules = {rule for _line, rule, _message in errors}
    assert {"實作召喚", "出題", "破折號"} <= rules


def test_homophone_rules_are_loaded_from_voice_style(tmp_path):
    linter = load_linter()
    style = tmp_path / "voice-style.md"
    style.write_text(
        "| 別寫 | 改寫成 | 原因 |\n"
        "| --- | --- | --- |\n"
        "| 重跑一次 | 再跑一次 | 避免破音 |\n",
        encoding="utf-8",
    )

    assert linter.load_homophone_table(style)["重跑一次"] == (
        "再跑一次",
        "避免破音",
    )
