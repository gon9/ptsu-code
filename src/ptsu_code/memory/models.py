"""Session Memory のデータモデル。"""

from dataclasses import dataclass, field


@dataclass
class SessionMemoryConfig:
    """Session Memory の設定。

    Claude Code の SessionMemoryConfig に準拠しつつ、
    ptsu-code の短めセッションに合わせて閾値を調整している。
    """

    minimum_tokens_to_init: int = 8_000
    """初期化に必要な最低トークン数。"""

    minimum_tokens_between_update: int = 4_000
    """更新間の最低トークン増加量。"""

    tool_calls_between_updates: int = 3
    """更新間の最低ツール呼び出し数。"""

    max_section_length_tokens: int = 2_000
    """セクションごとの最大トークン数。"""

    max_total_tokens: int = 12_000
    """メモリファイル全体の最大トークン数。"""


@dataclass
class SessionMemoryState:
    """Session Memory の実行時状態。"""

    initialized: bool = False
    """初期化閾値を超えたか。"""

    tokens_at_last_extraction: int = 0
    """最後に抽出を実行した時点の会話トークン数。"""

    tool_calls_since_last_extraction: int = 0
    """最後の抽出以降のツール呼び出し数。"""

    conversation: list[dict[str, str]] = field(default_factory=list)
    """会話履歴。各要素は {"user": str, "assistant": str}。"""

    def add_turn(self, user_msg: str, assistant_msg: str, tool_call_count: int = 0) -> None:
        """1ターン分のデータを追加する。

        Args:
            user_msg: ユーザーメッセージ
            assistant_msg: アシスタントの応答
            tool_call_count: このターンで実行されたツール呼び出し数
        """
        self.conversation.append({"user": user_msg, "assistant": assistant_msg})
        self.tool_calls_since_last_extraction += tool_call_count

    def total_chars(self) -> int:
        """会話全体の文字数を返す。

        Returns:
            会話全体の文字数
        """
        return sum(len(t["user"]) + len(t["assistant"]) for t in self.conversation)

    def chars_since_last_extraction(self) -> int:
        """最後の抽出以降の文字数増加量を返す。

        Returns:
            最後の抽出以降の文字数
        """
        total = self.total_chars()
        return total - (self.tokens_at_last_extraction * 4)

    def record_extraction(self) -> None:
        """抽出完了を記録する。状態をリセットする。"""
        self.tokens_at_last_extraction = self.total_chars() // 4
        self.tool_calls_since_last_extraction = 0
