"""triggers.py のユニットテスト。"""

import pytest

from ptsu_code.memory.models import SessionMemoryConfig, SessionMemoryState
from ptsu_code.memory.triggers import estimate_tokens, should_extract


class TestEstimateTokens:
    """estimate_tokens のテスト。"""

    def test_empty_string(self) -> None:
        """空文字列は 0 トークン。"""
        assert estimate_tokens("") == 0

    def test_four_chars_is_one_token(self) -> None:
        """4文字 = 1トークン。"""
        assert estimate_tokens("abcd") == 1

    def test_larger_text(self) -> None:
        """大きなテキストの概算。"""
        text = "a" * 400
        assert estimate_tokens(text) == 100


class TestShouldExtract:
    """should_extract のテスト。"""

    @pytest.fixture()
    def config(self) -> SessionMemoryConfig:
        """テスト用に閾値を小さくした config。"""
        return SessionMemoryConfig(
            minimum_tokens_to_init=100,
            minimum_tokens_between_update=50,
            tool_calls_between_updates=2,
        )

    def test_returns_false_when_no_conversation(self, config) -> None:
        """会話がない場合は False。"""
        state = SessionMemoryState()
        assert should_extract(state, config) is False

    def test_returns_false_below_init_threshold(self, config) -> None:
        """初期化閾値未満の場合は False。"""
        state = SessionMemoryState()
        state.add_turn("a" * 10, "b" * 10)
        assert should_extract(state, config) is False

    def test_initialized_when_threshold_met(self, config) -> None:
        """初期化閾値を超えると initialized が True になる。"""
        state = SessionMemoryState()
        state.add_turn("a" * 200, "b" * 200)
        should_extract(state, config)
        assert state.initialized is True

    def test_returns_true_when_thresholds_met(self, config) -> None:
        """トークンとツールコールの両方の閾値を超えた場合は True。"""
        state = SessionMemoryState()
        state.add_turn("a" * 200, "b" * 200, tool_call_count=3)
        assert should_extract(state, config) is True

    def test_returns_false_below_update_threshold_after_init(self, config) -> None:
        """初期化後でもトークン増加が不足していれば False。"""
        state = SessionMemoryState()
        state.add_turn("a" * 200, "b" * 200)
        state.record_extraction()

        state.add_turn("x" * 5, "y" * 5)
        assert should_extract(state, config) is False

    def test_returns_true_after_second_large_turn(self, config) -> None:
        """初期化後に大きなターンが追加されたら True。"""
        state = SessionMemoryState()
        state.add_turn("a" * 200, "b" * 200)
        state.record_extraction()

        state.add_turn("c" * 200, "d" * 200)
        assert should_extract(state, config) is True

    def test_state_not_initialized_if_below_threshold(self, config) -> None:
        """閾値未満では initialized が False のまま。"""
        state = SessionMemoryState()
        state.add_turn("x" * 5, "y" * 5)
        should_extract(state, config)
        assert state.initialized is False
