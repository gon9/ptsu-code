"""Evaluation メトリクスのデータモデル。"""

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime


def _now_iso() -> str:
    """現在時刻を ISO 8601 形式で返す。"""
    return datetime.now(tz=UTC).isoformat()


@dataclass
class TurnMetrics:
    """1 ターン分のメトリクス。"""

    session_id: str
    turn_index: int
    timestamp: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    had_tool_calls: bool
    finish_reason: str

    def to_dict(self) -> dict:
        """辞書形式に変換する。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TurnMetrics":
        """辞書から復元する。"""
        return cls(**data)


@dataclass
class SessionMetrics:
    """1 セッション分のメトリクス。"""

    session_id: str
    started_at: str = field(default_factory=_now_iso)
    ended_at: str | None = None
    provider: str = ""
    model: str = ""
    turns: list[TurnMetrics] = field(default_factory=list)

    def add_turn(self, turn: TurnMetrics) -> None:
        """ターンメトリクスを追加する。

        Args:
            turn: ターンメトリクス
        """
        self.turns.append(turn)

    def finalize(self) -> None:
        """セッションを終了済みにする。"""
        self.ended_at = _now_iso()

    @property
    def total_cost_usd(self) -> float:
        """セッション合計コスト (USD)。"""
        return sum(t.cost_usd for t in self.turns)

    @property
    def total_input_tokens(self) -> int:
        """セッション合計入力トークン数。"""
        return sum(t.input_tokens for t in self.turns)

    @property
    def total_output_tokens(self) -> int:
        """セッション合計出力トークン数。"""
        return sum(t.output_tokens for t in self.turns)

    @property
    def turn_count(self) -> int:
        """ターン数。"""
        return len(self.turns)

    def to_dict(self) -> dict:
        """辞書形式に変換する。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SessionMetrics":
        """辞書から復元する。"""
        turns = [TurnMetrics.from_dict(t) for t in data.pop("turns", [])]
        session = cls(**data)
        session.turns = turns
        return session
