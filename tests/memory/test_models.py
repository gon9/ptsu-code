"""SessionMemoryConfig / SessionMemoryState のユニットテスト。"""


from ptsu_code.memory.models import SessionMemoryConfig, SessionMemoryState


class TestSessionMemoryConfig:
    """SessionMemoryConfig のテスト。"""

    def test_default_values(self) -> None:
        """デフォルト値が設定されていること。"""
        config = SessionMemoryConfig()
        assert config.minimum_tokens_to_init == 8_000
        assert config.minimum_tokens_between_update == 4_000
        assert config.tool_calls_between_updates == 3
        assert config.max_section_length_tokens == 2_000
        assert config.max_total_tokens == 12_000

    def test_custom_values(self) -> None:
        """カスタム値で初期化できること。"""
        config = SessionMemoryConfig(minimum_tokens_to_init=1_000)
        assert config.minimum_tokens_to_init == 1_000


class TestSessionMemoryState:
    """SessionMemoryState のテスト。"""

    def test_initial_state(self) -> None:
        """初期状態が正しいこと。"""
        state = SessionMemoryState()
        assert state.initialized is False
        assert state.tokens_at_last_extraction == 0
        assert state.tool_calls_since_last_extraction == 0
        assert state.conversation == []

    def test_add_turn_appends_conversation(self) -> None:
        """add_turn が会話を追加すること。"""
        state = SessionMemoryState()
        state.add_turn("hello", "world")
        assert len(state.conversation) == 1
        assert state.conversation[0] == {"user": "hello", "assistant": "world"}

    def test_add_turn_accumulates_tool_calls(self) -> None:
        """add_turn がツール呼び出し数を累積すること。"""
        state = SessionMemoryState()
        state.add_turn("a", "b", tool_call_count=2)
        state.add_turn("c", "d", tool_call_count=3)
        assert state.tool_calls_since_last_extraction == 5

    def test_total_chars(self) -> None:
        """total_chars が全文字数を返すこと。"""
        state = SessionMemoryState()
        state.add_turn("abc", "de")
        state.add_turn("f", "ghij")
        assert state.total_chars() == 3 + 2 + 1 + 4

    def test_chars_since_last_extraction_initially_zero(self) -> None:
        """初回は chars_since_last_extraction が total と一致すること。"""
        state = SessionMemoryState()
        state.add_turn("a" * 100, "b" * 100)
        assert state.chars_since_last_extraction() == state.total_chars()

    def test_record_extraction_resets_state(self) -> None:
        """record_extraction が tool_calls をリセットし tokens を記録すること。"""
        state = SessionMemoryState()
        state.add_turn("a" * 400, "b" * 400, tool_call_count=5)
        state.record_extraction()

        assert state.tool_calls_since_last_extraction == 0
        assert state.tokens_at_last_extraction == 800 // 4

    def test_chars_since_last_extraction_after_record(self) -> None:
        """record_extraction 後は新しいターン分だけ差分が出ること。"""
        state = SessionMemoryState()
        state.add_turn("a" * 400, "b" * 400)
        state.record_extraction()

        state.add_turn("c" * 100, "d" * 100)
        chars = state.chars_since_last_extraction()
        assert chars == 200
