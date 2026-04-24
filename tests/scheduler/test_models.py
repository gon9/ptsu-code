"""ScheduledTask モデルのテスト。"""

from datetime import UTC, datetime, timedelta

import pytest

from ptsu_code.scheduler.models import ScheduledTask


class TestScheduledTask:
    """ScheduledTask のテスト。"""

    def test_default_id_has_prefix(self) -> None:
        """自動生成IDは sch_ プレフィックスを持つ。"""
        task = ScheduledTask(cron="*/5 * * * *", prompt="test")
        assert task.id.startswith("sch_")
        assert len(task.id) == 16  # sch_ + 12 hex chars

    def test_to_dict_roundtrip(self) -> None:
        """to_dict / from_dict のラウンドトリップが一致する。"""
        original = ScheduledTask(
            cron="0 9 * * 1-5",
            prompt="daily standup",
            recurring=True,
            durable=True,
        )
        restored = ScheduledTask.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.cron == original.cron
        assert restored.prompt == original.prompt
        assert restored.recurring == original.recurring
        assert restored.durable == original.durable

    def test_from_dict_missing_required_raises(self) -> None:
        """必須フィールド欠落時は ValueError。"""
        with pytest.raises(ValueError, match="Missing required"):
            ScheduledTask.from_dict({"id": "x", "cron": "* * * * *"})

    def test_is_expired_none_expires_at(self) -> None:
        """expires_at が None なら常に有効。"""
        task = ScheduledTask(cron="*/5 * * * *", prompt="test")
        assert not task.is_expired()

    def test_is_expired_past_date(self) -> None:
        """期限が過去なら期限切れ。"""
        past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        task = ScheduledTask(cron="*/5 * * * *", prompt="test", expires_at=past)
        assert task.is_expired()

    def test_is_expired_future_date(self) -> None:
        """期限が未来なら有効。"""
        future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        task = ScheduledTask(cron="*/5 * * * *", prompt="test", expires_at=future)
        assert not task.is_expired()
