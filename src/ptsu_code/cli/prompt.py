"""対話入力モジュール。"""

from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory


class UserPrompt:
    """ユーザー入力を管理するクラス。"""

    def __init__(self, history_file: Path | None = None) -> None:
        """初期化。

        Args:
            history_file: 履歴ファイルのパス
        """
        self.history_file = history_file
        if history_file:
            history_file.parent.mkdir(parents=True, exist_ok=True)
            self.session: PromptSession[str] = PromptSession(history=FileHistory(str(history_file)))
        else:
            self.session = PromptSession()

    def get_input(self, prompt: str = "> ") -> str | None:
        """ユーザー入力を取得する。

        Args:
            prompt: プロンプト文字列

        Returns:
            ユーザー入力文字列。Ctrl+D/Ctrl+Cの場合はNone
        """
        try:
            user_input = self.session.prompt(prompt)
            return user_input.strip()
        except (EOFError, KeyboardInterrupt):
            return None
