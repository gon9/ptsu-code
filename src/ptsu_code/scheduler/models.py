"""スケジュールタスクのデータモデル。"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def _now_iso() -> str:
    """現在時刻をISO 8601形式(UTC)で返す。"""
    return datetime.now(UTC).isoformat()


def _new_task_id() -> str:
    """新しいタスクIDを生成する。"""
    return f"sch_{uuid.uuid4().hex[:12]}"


@dataclass
class ScheduledTask:
    """スケジュールされたタスク。

    Attributes:
        id: タスクID (例: sch_abc123)
        cron: 5-field cron式 (例: "0 9 * * 1-5")
        prompt: 発火時にエージェントへ渡すプロンプト
        recurring: Trueなら繰り返し、Falseなら一回のみ
        durable: Trueなら永続化、Falseならインメモリのみ
        created_at: 作成時刻 (ISO 8601, UTC)
        last_fired_at: 直近の発火時刻 (ISO 8601, UTC)、未発火時はNone
        expires_at: 有効期限 (ISO 8601, UTC)、Noneなら無期限
    """

    cron: str
    prompt: str
    recurring: bool = True
    durable: bool = False
    id: str = field(default_factory=_new_task_id)
    created_at: str = field(default_factory=_now_iso)
    last_fired_at: str | None = None
    expires_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換する(JSON永続化用)。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScheduledTask:
        """辞書から復元する。

        Args:
            data: to_dict()で生成された辞書

        Returns:
            復元されたScheduledTask

        Raises:
            ValueError: 必須フィールドが欠落している場合
        """
        required = {"id", "cron", "prompt", "recurring", "durable", "created_at"}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
        return cls(
            id=data["id"],
            cron=data["cron"],
            prompt=data["prompt"],
            recurring=data["recurring"],
            durable=data["durable"],
            created_at=data["created_at"],
            last_fired_at=data.get("last_fired_at"),
            expires_at=data.get("expires_at"),
        )

    def is_expired(self, now: datetime | None = None) -> bool:
        """タスクが有効期限切れかを返す。

        Args:
            now: 現在時刻(UTC)、省略時はdatetime.now(timezone.utc)

        Returns:
            期限切れならTrue
        """
        if self.expires_at is None:
            return False
        now = now or datetime.now(UTC)
        expires = datetime.fromisoformat(self.expires_at)
        return now >= expires
