"""SchedulerDaemon のテスト。"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ptsu_code.scheduler.idle import IdleTracker
from ptsu_code.scheduler.models import ScheduledTask
from ptsu_code.scheduler.runner import SchedulerDaemon
from ptsu_code.scheduler.storage import ScheduleStore


@pytest.fixture
def store(tmp_path: Path) -> ScheduleStore:
    """一時 ScheduleStore を返す。"""
    return ScheduleStore(store_path=tmp_path / "tasks.json")


@pytest.fixture
def idle_tracker() -> IdleTracker:
    """idle=True の IdleTracker を返す。"""
    tracker = IdleTracker()
    tracker.set_idle(True)
    return tracker


class _FakeClock:
    """テスト用の時計。"""

    def __init__(self, initial: datetime) -> None:
        self.current = initial

    def __call__(self) -> datetime:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current = self.current + timedelta(seconds=seconds)


class TestSchedulerDaemonTick:
    """SchedulerDaemon.tick のテスト(スレッドを使わない単体テスト)。"""

    def test_tick_does_not_fire_when_busy(self, store: ScheduleStore) -> None:
        """busy (is_idle=False) のとき発火しない。"""
        tracker = IdleTracker()  # default busy
        clock = _FakeClock(datetime(2026, 4, 24, 10, 0, 0))
        daemon = SchedulerDaemon(store, tracker, time_provider=clock)
        store.add(
            ScheduledTask(
                cron="*/5 * * * *",
                prompt="test",
                durable=False,
                created_at="2026-04-24T09:00:00+00:00",
            )
        )
        fired = daemon.tick()
        assert fired == []

    def test_tick_fires_when_due(
        self, store: ScheduleStore, idle_tracker: IdleTracker
    ) -> None:
        """アイドル中で発火時刻を過ぎていれば発火する。"""
        # 10:00 時点で実行、5分毎タスクは 09:05 分起点で次は 09:10
        clock = _FakeClock(datetime(2026, 4, 24, 10, 0, 0))
        daemon = SchedulerDaemon(store, idle_tracker, time_provider=clock)
        task = ScheduledTask(
            cron="*/5 * * * *",
            prompt="do it",
            durable=False,
            recurring=True,
            created_at="2026-04-24T09:00:00+00:00",
        )
        store.add(task)
        fired = daemon.tick()
        assert len(fired) == 1
        assert fired[0].task_id == task.id
        assert fired[0].prompt == "do it"

    def test_tick_does_not_fire_before_due(
        self, store: ScheduleStore, idle_tracker: IdleTracker
    ) -> None:
        """発火時刻前は発火しない。"""
        # 09:01 では *5 分毎 / base 09:00 の場合 next は 09:05
        clock = _FakeClock(datetime(2026, 4, 24, 9, 1, 0))
        daemon = SchedulerDaemon(store, idle_tracker, time_provider=clock)
        store.add(
            ScheduledTask(
                cron="*/5 * * * *",
                prompt="test",
                durable=False,
                created_at="2026-04-24T09:00:00+00:00",
            )
        )
        fired = daemon.tick()
        assert fired == []

    def test_recurring_task_remains_after_fire(
        self, store: ScheduleStore, idle_tracker: IdleTracker
    ) -> None:
        """recurring=True は発火後もストアに残る。"""
        clock = _FakeClock(datetime(2026, 4, 24, 10, 0, 0))
        daemon = SchedulerDaemon(store, idle_tracker, time_provider=clock)
        task = ScheduledTask(
            cron="*/5 * * * *",
            prompt="test",
            durable=False,
            recurring=True,
            created_at="2026-04-24T09:00:00+00:00",
        )
        store.add(task)
        daemon.tick()
        assert store.get(task.id) is not None
        # last_fired_at が更新される
        reloaded = store.get(task.id)
        assert reloaded is not None
        assert reloaded.last_fired_at is not None

    def test_one_shot_task_removed_after_fire(
        self, store: ScheduleStore, idle_tracker: IdleTracker
    ) -> None:
        """recurring=False は発火後に削除される。"""
        clock = _FakeClock(datetime(2026, 4, 24, 10, 0, 0))
        daemon = SchedulerDaemon(store, idle_tracker, time_provider=clock)
        task = ScheduledTask(
            cron="*/5 * * * *",
            prompt="once",
            durable=False,
            recurring=False,
            created_at="2026-04-24T09:00:00+00:00",
        )
        store.add(task)
        daemon.tick()
        assert store.get(task.id) is None

    def test_expired_task_removed_without_firing(
        self, store: ScheduleStore, idle_tracker: IdleTracker
    ) -> None:
        """期限切れタスクは発火せず削除される。"""
        clock = _FakeClock(datetime(2026, 4, 24, 10, 0, 0))
        daemon = SchedulerDaemon(store, idle_tracker, time_provider=clock)
        expired_iso = (
            datetime(2026, 4, 24, 9, 0, 0, tzinfo=UTC)
        ).isoformat()
        task = ScheduledTask(
            cron="*/5 * * * *",
            prompt="expired",
            durable=False,
            created_at="2026-04-24T08:00:00+00:00",
            expires_at=expired_iso,
        )
        store.add(task)
        fired = daemon.tick()
        assert fired == []
        assert store.get(task.id) is None

    def test_fire_event_added_to_queue(
        self, store: ScheduleStore, idle_tracker: IdleTracker
    ) -> None:
        """発火イベントは fire_queue に追加される。"""
        clock = _FakeClock(datetime(2026, 4, 24, 10, 0, 0))
        daemon = SchedulerDaemon(store, idle_tracker, time_provider=clock)
        store.add(
            ScheduledTask(
                cron="*/5 * * * *",
                prompt="queue test",
                durable=False,
                created_at="2026-04-24T09:00:00+00:00",
            )
        )
        daemon.tick()
        assert not daemon.fire_queue.empty()
        event = daemon.fire_queue.get_nowait()
        assert event.prompt == "queue test"

    def test_recurring_fires_only_once_per_tick(
        self, store: ScheduleStore, idle_tracker: IdleTracker
    ) -> None:
        """recurring タスクは1 tick で最大1回しか発火しない。

        (発火後 last_fired_at が更新され、同じ tick 内では再発火しない)
        """
        clock = _FakeClock(datetime(2026, 4, 24, 10, 0, 0))
        daemon = SchedulerDaemon(store, idle_tracker, time_provider=clock)
        store.add(
            ScheduledTask(
                cron="*/5 * * * *",
                prompt="test",
                durable=False,
                created_at="2026-04-24T09:00:00+00:00",
            )
        )
        fired1 = daemon.tick()
        fired2 = daemon.tick()
        assert len(fired1) == 1
        assert len(fired2) == 0


class TestSchedulerDaemonLifecycle:
    """start/stop のテスト。"""

    def test_start_stop(self, store: ScheduleStore) -> None:
        """start/stop が例外を投げない。"""
        tracker = IdleTracker()
        daemon = SchedulerDaemon(store, tracker, tick_interval=0.05)
        daemon.start()
        daemon.stop()

    def test_double_start_no_error(self, store: ScheduleStore) -> None:
        """複数回 start を呼んでも問題ない。"""
        tracker = IdleTracker()
        daemon = SchedulerDaemon(store, tracker, tick_interval=0.05)
        daemon.start()
        daemon.start()
        daemon.stop()
