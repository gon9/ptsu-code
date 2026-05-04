"""eval/models.py のユニットテスト。"""

import pytest

from ptsu_code.eval.models import SessionMetrics, TurnMetrics


def _make_turn(session_id: str = "s1", turn_index: int = 0, cost: float = 0.001) -> TurnMetrics:
    """テスト用 TurnMetrics を生成する。"""
    return TurnMetrics(
        session_id=session_id,
        turn_index=turn_index,
        timestamp="2026-05-04T00:00:00+00:00",
        provider="openai",
        model="gpt-5-mini",
        input_tokens=100,
        output_tokens=50,
        cost_usd=cost,
        latency_ms=200.0,
        had_tool_calls=False,
        finish_reason="stop",
    )


class TestTurnMetrics:
    """TurnMetrics のテスト。"""

    def test_to_dict_and_from_dict_roundtrip(self) -> None:
        """to_dict → from_dict でラウンドトリップできる。"""
        turn = _make_turn()
        restored = TurnMetrics.from_dict(turn.to_dict())
        assert restored == turn

    def test_to_dict_has_required_keys(self) -> None:
        """to_dict が必要なキーを含む。"""
        d = _make_turn().to_dict()
        for key in ("session_id", "turn_index", "provider", "model", "cost_usd", "latency_ms"):
            assert key in d


class TestSessionMetrics:
    """SessionMetrics のテスト。"""

    def test_initial_state(self) -> None:
        """初期状態のプロパティ確認。"""
        s = SessionMetrics(session_id="abc")
        assert s.turn_count == 0
        assert s.total_cost_usd == 0.0
        assert s.total_input_tokens == 0
        assert s.total_output_tokens == 0

    def test_add_turn_increments_count(self) -> None:
        """add_turn でターン数が増える。"""
        s = SessionMetrics(session_id="abc")
        s.add_turn(_make_turn(cost=0.001))
        s.add_turn(_make_turn(cost=0.002))
        assert s.turn_count == 2

    def test_total_cost_sums_turns(self) -> None:
        """total_cost_usd はターンのコスト合計。"""
        s = SessionMetrics(session_id="abc")
        s.add_turn(_make_turn(cost=0.001))
        s.add_turn(_make_turn(cost=0.002))
        assert s.total_cost_usd == pytest.approx(0.003, rel=1e-6)

    def test_total_tokens(self) -> None:
        """total_input/output_tokens が正しく集計される。"""
        s = SessionMetrics(session_id="abc")
        s.add_turn(_make_turn())
        assert s.total_input_tokens == 100
        assert s.total_output_tokens == 50

    def test_finalize_sets_ended_at(self) -> None:
        """finalize() で ended_at が設定される。"""
        s = SessionMetrics(session_id="abc")
        assert s.ended_at is None
        s.finalize()
        assert s.ended_at is not None

    def test_to_dict_from_dict_roundtrip(self) -> None:
        """to_dict → from_dict でラウンドトリップできる。"""
        s = SessionMetrics(session_id="abc", provider="openai", model="gpt-5-mini")
        s.add_turn(_make_turn())
        s.finalize()
        d = s.to_dict()
        restored = SessionMetrics.from_dict(d)
        assert restored.session_id == s.session_id
        assert restored.turn_count == s.turn_count
        assert restored.ended_at == s.ended_at
