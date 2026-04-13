"""CLI UIコンポーネントのテスト。"""

from io import StringIO

import pytest
from rich.console import Console

from ptsu_code.agent.sub_agents.base import AgentRole
from ptsu_code.cli.ui import (
    show_coordinator_dispatch,
    show_error,
    show_info,
    show_message,
    show_streaming_chunk,
    show_streaming_end,
    show_streaming_start,
    show_tool_execution,
    show_tool_result,
    show_welcome,
)


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


class TestShowStreaming:
    """ストリーミング表示関数のテスト。"""

    def test_show_streaming_start_assistant(self, monkeypatch, console_output):
        """assistantロールのストリーミング開始が表示されることを確認する。"""
        string_io, console = console_output
        monkeypatch.setattr("ptsu_code.cli.ui.console", console)
        show_streaming_start("assistant")
        output = string_io.getvalue()
        assert "Assistant" in output

    def test_show_streaming_start_custom_role(self, monkeypatch, console_output):
        """カスタムロールのストリーミング開始が表示されることを確認する。"""
        string_io, console = console_output
        monkeypatch.setattr("ptsu_code.cli.ui.console", console)
        show_streaming_start("custom")
        output = string_io.getvalue()
        assert "custom" in output

    def test_show_streaming_chunk(self, monkeypatch, console_output):
        """ストリーミングチャンクが表示されることを確認する。"""
        string_io, console = console_output
        monkeypatch.setattr("ptsu_code.cli.ui.console", console)
        show_streaming_chunk("hello chunk")
        output = string_io.getvalue()
        assert "hello chunk" in output

    def test_show_streaming_end(self, monkeypatch, console_output):
        """ストリーミング終了で改行されることを確認する。"""
        string_io, console = console_output
        monkeypatch.setattr("ptsu_code.cli.ui.console", console)
        show_streaming_end()
        output = string_io.getvalue()
        assert "\n" in output


class TestShowToolExecution:
    """show_tool_execution関数のテスト。"""

    def test_shows_tool_name(self, monkeypatch, console_output):
        """ツール名が表示されることを確認する。"""
        string_io, console = console_output
        monkeypatch.setattr("ptsu_code.cli.ui.console", console)
        show_tool_execution("read_file", {"path": "x.py"})
        output = string_io.getvalue()
        assert "read_file" in output

    def test_shows_args(self, monkeypatch, console_output):
        """引数が表示されることを確認する。"""
        string_io, console = console_output
        monkeypatch.setattr("ptsu_code.cli.ui.console", console)
        show_tool_execution("write_file", {"path": "out.py", "content": "code"})
        output = string_io.getvalue()
        assert "path" in output

    def test_long_args_truncated(self, monkeypatch, console_output):
        """長い引数が省略されることを確認する。"""
        string_io, console = console_output
        monkeypatch.setattr("ptsu_code.cli.ui.console", console)
        show_tool_execution("tool", {"content": "x" * 200, "path": "y" * 200})
        output = string_io.getvalue()
        assert "tool" in output
        assert "..." in output


class TestShowToolResult:
    """show_tool_result関数のテスト。"""

    def test_success_shows_check(self, monkeypatch, console_output):
        """成功時にチェックマークが表示されることを確認する。"""
        string_io, console = console_output
        monkeypatch.setattr("ptsu_code.cli.ui.console", console)
        show_tool_result("read_file", success=True, output="file contents")
        output = string_io.getvalue()
        assert "read_file" in output
        assert "file contents" in output

    def test_failure_shows_error(self, monkeypatch, console_output):
        """失敗時にエラーメッセージが表示されることを確認する。"""
        string_io, console = console_output
        monkeypatch.setattr("ptsu_code.cli.ui.console", console)
        show_tool_result("write_file", success=False, error="Permission denied")
        output = string_io.getvalue()
        assert "write_file" in output
        assert "Permission denied" in output

    def test_long_output_truncated(self, monkeypatch, console_output):
        """長い出力が省略されることを確認する。"""
        string_io, console = console_output
        monkeypatch.setattr("ptsu_code.cli.ui.console", console)
        long_output = "\n".join([f"line {i}" for i in range(20)])
        show_tool_result("grep", success=True, output=long_output)
        output = string_io.getvalue()
        assert "grep" in output
        assert "lines total" in output

    def test_success_no_output_shows_success(self, monkeypatch, console_output):
        """出力なし成功時にSuccessが表示されることを確認する。"""
        string_io, console = console_output
        monkeypatch.setattr("ptsu_code.cli.ui.console", console)
        show_tool_result("execute_command", success=True, output="")
        output = string_io.getvalue()
        assert "Success" in output

    def test_failure_no_error_shows_unknown(self, monkeypatch, console_output):
        """エラーメッセージなし失敗時にUnknown errorが表示されることを確認する。"""
        string_io, console = console_output
        monkeypatch.setattr("ptsu_code.cli.ui.console", console)
        show_tool_result("tool", success=False, error="")
        output = string_io.getvalue()
        assert "Unknown error" in output


class TestShowCoordinatorDispatch:
    """show_coordinator_dispatch関数のテスト。"""

    @pytest.mark.parametrize("role,agent_name", [
        (AgentRole.SEARCHER, "Searcher"),
        (AgentRole.CODER, "Coder"),
        (AgentRole.EXECUTOR, "Executor"),
        (AgentRole.GENERAL, "General"),
    ])
    def test_shows_agent_name(self, monkeypatch, console_output, role, agent_name):
        """各ロールのエージェント名が表示されることを確認する。"""
        string_io, console = console_output
        monkeypatch.setattr("ptsu_code.cli.ui.console", console)
        show_coordinator_dispatch(role, agent_name)
        output = string_io.getvalue()
        assert agent_name in output

    def test_shows_intent_label_when_provided(self, monkeypatch, console_output):
        """intent_labelが提供されると表示されることを確認する。"""
        string_io, console = console_output
        monkeypatch.setattr("ptsu_code.cli.ui.console", console)
        show_coordinator_dispatch(AgentRole.SEARCHER, "Searcher", intent_label="SEARCH")
        output = string_io.getvalue()
        assert "SEARCH" in output

    def test_no_label_when_not_provided(self, monkeypatch, console_output):
        """intent_labelが空のとき括弧が表示されないことを確認する。"""
        string_io, console = console_output
        monkeypatch.setattr("ptsu_code.cli.ui.console", console)
        show_coordinator_dispatch(AgentRole.CODER, "Coder")
        output = string_io.getvalue()
        assert "(" not in output or "Coder" in output
