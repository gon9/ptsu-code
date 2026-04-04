"""プロンプト入力のテスト。"""

from unittest.mock import MagicMock, patch

import pytest

from ptsu_code.cli.prompt import UserPrompt


class TestUserPrompt:
    """UserPromptクラスのテスト。"""

    def test_init_without_history_file(self):
        """履歴ファイルなしで初期化できることを確認する。"""
        prompt = UserPrompt()
        assert prompt.history_file is None
        assert prompt.session is not None

    def test_init_with_history_file(self, tmp_path):
        """履歴ファイルありで初期化できることを確認する。"""
        history_file = tmp_path / "history.txt"
        prompt = UserPrompt(history_file=history_file)
        assert prompt.history_file == history_file
        assert prompt.session is not None
        assert history_file.parent.exists()

    @pytest.mark.parametrize(
        ("user_input", "expected"),
        [
            ("hello", "hello"),
            ("  spaces  ", "spaces"),
            ("", ""),
        ],
    )
    def test_get_input_normal(self, user_input, expected):
        """正常な入力が正しく処理されることを確認する。"""
        prompt = UserPrompt()
        with patch.object(prompt.session, "prompt", return_value=user_input):
            result = prompt.get_input("> ")
            assert result == expected

    @pytest.mark.parametrize(
        "exception",
        [EOFError, KeyboardInterrupt],
    )
    def test_get_input_interruption(self, exception):
        """中断時にNoneを返すことを確認する。"""
        prompt = UserPrompt()
        with patch.object(prompt.session, "prompt", side_effect=exception):
            result = prompt.get_input("> ")
            assert result is None

    def test_get_input_custom_prompt(self):
        """カスタムプロンプトが使用されることを確認する。"""
        prompt = UserPrompt()
        mock_session = MagicMock()
        mock_session.prompt.return_value = "test"
        prompt.session = mock_session

        prompt.get_input("Custom > ")
        mock_session.prompt.assert_called_once_with("Custom > ")
