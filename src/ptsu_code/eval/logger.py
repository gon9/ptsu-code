"""EvalLogger — セッションメトリクスの記録・読み込み。

データは ~/.ptsu/eval/sessions.jsonl に JSONL 形式で追記する。
"""

import json
from pathlib import Path

from ptsu_code.eval.models import SessionMetrics

DEFAULT_LOG_DIR = Path.home() / ".ptsu" / "eval"


class EvalLogger:
    """セッションメトリクスを JSONL ファイルに記録するロガー。"""

    def __init__(self, log_dir: Path | None = None) -> None:
        """初期化。

        Args:
            log_dir: ログディレクトリ。None の場合は DEFAULT_LOG_DIR を使用。
        """
        self.log_dir = log_dir or DEFAULT_LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = self.log_dir / "sessions.jsonl"

    def save(self, session: SessionMetrics) -> None:
        """セッションメトリクスを JSONL に追記する。

        Args:
            session: 保存するセッションメトリクス
        """
        with self._log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(session.to_dict(), ensure_ascii=False) + "\n")

    def load_all(self) -> list[SessionMetrics]:
        """全セッションを読み込む。

        Returns:
            セッションメトリクスのリスト。ファイルが存在しない場合は空リスト。
        """
        if not self._log_file.exists():
            return []

        sessions: list[SessionMetrics] = []
        with self._log_file.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    sessions.append(SessionMetrics.from_dict(data))
                except (json.JSONDecodeError, TypeError):
                    continue
        return sessions

    def clear(self) -> None:
        """ログファイルを削除する（テスト用）。"""
        if self._log_file.exists():
            self._log_file.unlink()
