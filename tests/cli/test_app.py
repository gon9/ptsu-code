"""CLIアプリケーションのテスト。"""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from ptsu_code import __version__
from ptsu_code.cli.app import app, main
from ptsu_code.exceptions import PTSUError

runner = CliRunner()


class TestVersionCommand:
    """versionコマンドのテスト。"""

    def test_version_command(self):
        """versionコマンドが正しく動作することを確認する。"""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert f"PTSU version {__version__}" in result.stdout


class TestHelpCommand:
    """helpコマンドのテスト。"""

    def test_help_command(self):
        """helpオプションが正しく表示されることを確認する。"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "PTSU - AI Agent CLI" in result.stdout

    def test_chat_help_command(self):
        """chatコマンドのhelpが正しく表示されることを確認する。"""
        result = runner.invoke(app, ["chat", "--help"])
        assert result.exit_code == 0
        assert "対話モードを起動する" in result.stdout


class TestChatCommand:
    """chatコマンドのテスト。"""

    def test_chat_command_exit(self):
        """exitコマンドで終了することを確認する。"""
        result = runner.invoke(app, ["chat"], input="exit\n")
        assert result.exit_code == 0
        assert "Goodbye!" in result.stdout

    def test_chat_command_quit(self):
        """quitコマンドで終了することを確認する。"""
        result = runner.invoke(app, ["chat"], input="quit\n")
        assert result.exit_code == 0
        assert "Goodbye!" in result.stdout

    def test_chat_command_with_verbose(self):
        """verboseオプションが正しく動作することを確認する。"""
        result = runner.invoke(app, ["chat", "--verbose"], input="exit")
        assert result.exit_code == 0
        assert "Goodbye!" in result.stdout

    def test_chat_command_empty_input(self):
        """空入力が正しく処理されることを確認する。"""
        result = runner.invoke(app, ["chat"], input="\n\nexit")
        assert result.exit_code == 0

    def test_chat_command_with_exception(self):
        """例外発生時のエラーハンドリングを確認する。"""
        with patch("ptsu_code.cli.app.UserPrompt") as mock_prompt:
            mock_instance = MagicMock()
            mock_instance.get_input.side_effect = PTSUError("Test error")
            mock_prompt.return_value = mock_instance

            result = runner.invoke(app, ["chat"])
            assert result.exit_code == 1
            assert "Test error" in result.stdout


class TestMainFunction:
    """main関数のテスト。"""

    def test_main_function(self):
        """main関数が正しく動作することを確認する。"""
        with patch("ptsu_code.cli.app.app") as mock_app:
            main()
            mock_app.assert_called_once()
