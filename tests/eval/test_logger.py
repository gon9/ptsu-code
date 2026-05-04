"""eval/logger.py のユニットテスト。"""

import tempfile
from pathlib import Path

from ptsu_code.eval.logger import EvalLogger
from ptsu_code.eval.models import SessionMetrics, TurnMetrics


def _make_session(session_id: str = "test-session") -> SessionMetrics:
    """テスト用 SessionMetrics を生成する。"""
    s = SessionMetrics(session_id=session_id, provider="openai", model="gpt-5-mini")
    s.add_turn(TurnMetrics(
        session_id=session_id,
        turn_index=0,
        timestamp="2026-05-04T00:00:00+00:00",
        provider="openai",
        model="gpt-5-mini",
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.001,
        latency_ms=150.0,
        had_tool_calls=False,
        finish_reason="stop",
    ))
    s.finalize()
    return s


class TestEvalLogger:
    """EvalLogger のテスト。"""

    def test_save_and_load_roundtrip(self) -> None:
        """save → load_all でラウンドトリップできる。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = EvalLogger(log_dir=Path(tmpdir))
            session = _make_session()
            logger.save(session)

            loaded = logger.load_all()

        assert len(loaded) == 1
        assert loaded[0].session_id == session.session_id
        assert loaded[0].turn_count == 1

    def test_load_all_empty_when_no_file(self) -> None:
        """ファイルが存在しない場合は空リストを返す。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = EvalLogger(log_dir=Path(tmpdir))
            assert logger.load_all() == []

    def test_multiple_sessions_are_appended(self) -> None:
        """複数セッションを追記して全件取得できる。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = EvalLogger(log_dir=Path(tmpdir))
            logger.save(_make_session("s1"))
            logger.save(_make_session("s2"))
            logger.save(_make_session("s3"))

            loaded = logger.load_all()

        assert len(loaded) == 3
        ids = {s.session_id for s in loaded}
        assert ids == {"s1", "s2", "s3"}

    def test_clear_removes_file(self) -> None:
        """clear() でファイルが削除される。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = EvalLogger(log_dir=Path(tmpdir))
            logger.save(_make_session())
            logger.clear()
            assert logger.load_all() == []

    def test_corrupt_line_is_skipped(self) -> None:
        """壊れた行はスキップして残りを返す。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = EvalLogger(log_dir=Path(tmpdir))
            logger.save(_make_session("valid"))

            log_file = Path(tmpdir) / "sessions.jsonl"
            with log_file.open("a") as f:
                f.write("this is not valid json\n")

            loaded = logger.load_all()

        assert len(loaded) == 1
        assert loaded[0].session_id == "valid"
