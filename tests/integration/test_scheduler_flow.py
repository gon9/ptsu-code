"""スケジュール機能の統合テスト (UAT-SCH-01〜05)。"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from ptsu_code.agent.tools.schedule_tools import (
    ScheduleCreateTool,
    ScheduleDeleteTool,
    ScheduleListTool,
)
from ptsu_code.scheduler.idle import IdleTracker
from ptsu_code.scheduler.runner import SchedulerDaemon
from ptsu_code.scheduler.storage import ScheduleStore


@pytest.fixture
def store(tmp_path: Path) -> ScheduleStore:
    """一時 ScheduleStore を返す。"""
    return ScheduleStore(store_path=tmp_path / ".ptsu" / "scheduled_tasks.json")


class TestUatSchedulerFlow:
    """UAT-SCH-01〜05 を自動化した統合テスト。"""

    def test_uat_sch_01_create_persists_json(self, tmp_path: Path) -> None:
        """UAT-SCH-01: durable=True で JSON ファイルに書き込まれる。"""
        store_path = tmp_path / ".ptsu" / "scheduled_tasks.json"
        store = ScheduleStore(store_path=store_path)
        tool = ScheduleCreateTool(store)
        result = tool.execute(
            cron="0 9 * * *",
            prompt="daily standup",
            durable=True,
        )
        assert result.success
        assert store_path.exists()
        import json
        data = json.loads(store_path.read_text())
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["prompt"] == "daily standup"

    def test_uat_sch_02_list_shows_entries(self, store: ScheduleStore) -> None:
        """UAT-SCH-02: schedule_list で登録済みタスクが確認できる。"""
        create = ScheduleCreateTool(store)
        create.execute(cron="0 9 * * *", prompt="a")
        create.execute(cron="*/30 * * * *", prompt="b")

        list_tool = ScheduleListTool(store)
        result = list_tool.execute()
        assert result.success
        assert "a" in result.output
        assert "b" in result.output

    def test_uat_sch_03_delete_removes_task(self, store: ScheduleStore) -> None:
        """UAT-SCH-03: schedule_delete で削除できる。"""
        create = ScheduleCreateTool(store)
        create.execute(cron="0 9 * * *", prompt="temp")
        task_id = store.list_all()[0].id

        delete = ScheduleDeleteTool(store)
        result = delete.execute(id=task_id)
        assert result.success
        assert store.count() == 0

    def test_uat_sch_04_recurring_refires_one_shot_auto_removes(
        self, store: ScheduleStore
    ) -> None:
        """UAT-SCH-04: recurring=True は再登録、False は削除される。"""
        idle = IdleTracker()
        idle.set_idle(True)
        current = [datetime(2026, 4, 24, 10, 0, 0)]

        def clock() -> datetime:
            return current[0]

        daemon = SchedulerDaemon(store, idle, time_provider=clock)

        create = ScheduleCreateTool(store)
        create.execute(cron="*/5 * * * *", prompt="recur", recurring=True)
        create.execute(cron="*/5 * * * *", prompt="once", recurring=False)
        # 作成後タスクを過去に作成されたことにする (created_at を古くする)
        for t in store.list_all():
            updated_dict = t.to_dict()
            updated_dict["created_at"] = "2026-04-24T09:00:00+00:00"
            from ptsu_code.scheduler.models import ScheduledTask
            store.update(ScheduledTask.from_dict(updated_dict))

        fired = daemon.tick()
        assert len(fired) == 2

        # recurring は残る
        recurring_tasks = [t for t in store.list_all() if t.prompt == "recur"]
        assert len(recurring_tasks) == 1
        # one-shot は削除される
        one_shot = [t for t in store.list_all() if t.prompt == "once"]
        assert len(one_shot) == 0

        # 時刻を進めても recurring は再発火可能
        current[0] = datetime(2026, 4, 24, 10, 6, 0)
        fired2 = daemon.tick()
        assert len(fired2) == 1
        assert fired2[0].prompt == "recur"

    def test_uat_sch_05_durable_survives_session(self, tmp_path: Path) -> None:
        """UAT-SCH-05: durable=True のタスクは新セッションで復元される。"""
        store_path = tmp_path / ".ptsu" / "scheduled_tasks.json"

        # セッション1
        store1 = ScheduleStore(store_path=store_path)
        create = ScheduleCreateTool(store1)
        create.execute(
            cron="0 9 * * *",
            prompt="persistent",
            durable=True,
        )
        original_id = store1.list_all()[0].id

        # セッション2 (新インスタンス)
        store2 = ScheduleStore(store_path=store_path)
        assert store2.count() == 1
        loaded = store2.get(original_id)
        assert loaded is not None
        assert loaded.prompt == "persistent"
        assert loaded.durable is True

    def test_uat_sch_06_session_only_does_not_survive(self, tmp_path: Path) -> None:
        """UAT-SCH-06: durable=False のタスクは新セッションで失われる。"""
        store_path = tmp_path / ".ptsu" / "scheduled_tasks.json"
        store1 = ScheduleStore(store_path=store_path)
        ScheduleCreateTool(store1).execute(
            cron="*/5 * * * *", prompt="ephemeral", durable=False
        )
        assert store1.count() == 1

        store2 = ScheduleStore(store_path=store_path)
        assert store2.count() == 0

    def test_uat_sch_07_max_jobs_enforced(self, store: ScheduleStore) -> None:
        """UAT-SCH-07: MAX_JOBS=50 を超えたら拒否される。"""
        create = ScheduleCreateTool(store)
        for _ in range(50):
            result = create.execute(cron="*/5 * * * *", prompt="test")
            assert result.success
        # 51本目は失敗
        result = create.execute(cron="*/5 * * * *", prompt="overflow")
        assert not result.success
        assert "Too many" in (result.error or "")

    def test_uat_sch_08_busy_repl_blocks_fire(self, store: ScheduleStore) -> None:
        """UAT-SCH-08: busy (is_idle=False) のとき発火しない。"""
        idle = IdleTracker()  # default busy
        daemon = SchedulerDaemon(
            store,
            idle,
            time_provider=lambda: datetime(2026, 4, 24, 10, 0, 0),
        )
        create = ScheduleCreateTool(store)
        create.execute(cron="*/5 * * * *", prompt="test")
        # created_at を過去にして発火条件を満たす
        for t in store.list_all():
            updated_dict = t.to_dict()
            updated_dict["created_at"] = "2026-04-24T09:00:00+00:00"
            from ptsu_code.scheduler.models import ScheduledTask
            store.update(ScheduledTask.from_dict(updated_dict))

        fired = daemon.tick()
        assert fired == []  # busy なので発火しない

    def test_uat_sch_09_expired_recurring_removed(
        self, store: ScheduleStore
    ) -> None:
        """UAT-SCH-09: expires_at を過ぎた recurring タスクは削除される。"""
        idle = IdleTracker()
        idle.set_idle(True)
        daemon = SchedulerDaemon(
            store,
            idle,
            time_provider=lambda: datetime(2026, 5, 30, 10, 0, 0),
        )

        create = ScheduleCreateTool(store)
        result = create.execute(cron="0 9 * * *", prompt="expires")
        assert result.success
        task = store.list_all()[0]
        # expires_at は +30日。2026-05-30 なら >30日経過していないが、
        # 1年後なら確実に expired
        from ptsu_code.scheduler.models import ScheduledTask
        expired_dict = task.to_dict()
        expired_dict["expires_at"] = "2026-04-01T00:00:00+00:00"  # 過去
        store.update(ScheduledTask.from_dict(expired_dict))

        daemon.tick()
        assert store.get(task.id) is None

    def test_uat_sch_10_invalid_cron_rejected(self, store: ScheduleStore) -> None:
        """UAT-SCH-10: 不正な cron 式は拒否される。"""
        tool = ScheduleCreateTool(store)
        result = tool.execute(cron="not-a-cron", prompt="bad")
        assert not result.success
        assert "Invalid cron" in (result.error or "")

    def test_uat_sch_11_expires_at_set_for_recurring(
        self, store: ScheduleStore
    ) -> None:
        """UAT-SCH-11: recurring=True は 30 日の expires_at が設定される。"""
        tool = ScheduleCreateTool(store)
        tool.execute(cron="0 9 * * *", prompt="test", recurring=True)
        task = store.list_all()[0]
        assert task.expires_at is not None
        expires = datetime.fromisoformat(task.expires_at)
        now_utc = datetime.now(expires.tzinfo)
        delta = expires - now_utc
        # おおむね30日前後
        assert timedelta(days=29) < delta < timedelta(days=31)
