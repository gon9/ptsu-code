"""CLI UIコンポーネントのテスト。"""

from io import StringIO

import pytest
from rich.console import Console

from ptsu_code.cli.ui import show_error, show_info, show_message, show_welcome


@pytest.fixture
def console_output():
    """コンソール出力をキャプチャするフィクスチャ。"""
    string_io = StringIO()
    console = Console(file=string_io, force_terminal=True, width=120)
    return string_io, console


class TestShowWelcome:
    """show_welcome関数のテスト。"""

    def test_show_welcome_displays_version(self, monkeypatch, console_output):
        """ウェルカム画面にバージョンが表示されることを確認する。"""
        string_io, console = console_output
        monkeypatch.setattr("ptsu_code.cli.ui.console", console)

        show_welcome("0.1.0")
        output = string_io.getvalue()

        assert "PTSU" in output
        assert "0.1.0" in output
        assert "exit" in output or "quit" in output


class TestShowMessage:
    """show_message関数のテスト。"""

    @pytest.mark.parametrize(
        ("role", "content", "expected_prefix"),
        [
            ("user", "Hello", "You:"),
            ("assistant", "Hi there", "Assistant:"),
            ("system", "Info message", "System:"),
            ("unknown", "Test", "Test"),
        ],
    )
    def test_show_message_with_different_roles(self, monkeypatch, console_output, role, content, expected_prefix):
        """異なるロールでメッセージが正しく表示されることを確認する。"""
        string_io, console = console_output
        monkeypatch.setattr("ptsu_code.cli.ui.console", console)

        show_message(role, content)
        output = string_io.getvalue()

        if role in ("user", "assistant", "system"):
            assert expected_prefix in output
        assert content in output


class TestShowError:
    """show_error関数のテスト。"""

    def test_show_error_displays_message(self, monkeypatch, console_output):
        """エラーメッセージが正しく表示されることを確認する。"""
        string_io, console = console_output
        monkeypatch.setattr("ptsu_code.cli.ui.console", console)

        show_error("Test error message")
        output = string_io.getvalue()

        assert "Error:" in output
        assert "Test error message" in output


class TestShowInfo:
    """show_info関数のテスト。"""

    def test_show_info_displays_message(self, monkeypatch, console_output):
        """情報メッセージが正しく表示されることを確認する。"""
        string_io, console = console_output
        monkeypatch.setattr("ptsu_code.cli.ui.console", console)

        show_info("Test info message")
        output = string_io.getvalue()

        assert "Test info message" in output
