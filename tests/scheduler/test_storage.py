"""ScheduleStore のテスト。"""

import json
from pathlib import Path

import pytest

from ptsu_code.scheduler.models import ScheduledTask
from ptsu_code.scheduler.storage import MAX_JOBS, ScheduleStore, ScheduleStoreError


@pytest.fixture
def store_path(tmp_path: Path) -> Path:
    """一時ファイルパスを返す。"""
    return tmp_path / ".ptsu" / "scheduled_tasks.json"


class TestScheduleStore:
    """ScheduleStore のテスト。"""

    def test_empty_store_list_returns_empty(self, store_path: Path) -> None:
        """空ストアはリストが空。"""
        store = ScheduleStore(store_path=store_path)
        assert store.list_all() == []
        assert store.count() == 0

    def test_add_session_task(self, store_path: Path) -> None:
        """session-only タスク追加はファイルを作らない。"""
        store = ScheduleStore(store_path=store_path)
        task = ScheduledTask(cron="*/5 * * * *", prompt="test", durable=False)
        store.add(task)
        assert store.count() == 1
        assert not store_path.exists()

    def test_add_durable_task_persists(self, store_path: Path) -> None:
        """durable タスク追加でファイル作成される。"""
        store = ScheduleStore(store_path=store_path)
        task = ScheduledTask(cron="0 9 * * *", prompt="daily", durable=True)
        store.add(task)
        assert store_path.exists()
        data = json.loads(store_path.read_text(encoding="utf-8"))
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["id"] == task.id

    def test_load_existing_durable_tasks(self, store_path: Path) -> None:
        """既存の永続化ファイルからdurableタスクを復元する。"""
        store1 = ScheduleStore(store_path=store_path)
        task = ScheduledTask(cron="0 9 * * *", prompt="daily", durable=True)
        store1.add(task)

        store2 = ScheduleStore(store_path=store_path)
        assert store2.count() == 1
        loaded = store2.get(task.id)
        assert loaded is not None
        assert loaded.prompt == "daily"

    def test_session_tasks_not_persisted(self, store_path: Path) -> None:
        """session-only タスクは別ストアに引き継がれない。"""
        store1 = ScheduleStore(store_path=store_path)
        store1.add(ScheduledTask(cron="*/5 * * * *", prompt="ephemeral", durable=False))

        store2 = ScheduleStore(store_path=store_path)
        assert store2.count() == 0

    def test_delete_durable_task(self, store_path: Path) -> None:
        """durable タスク削除でファイルが更新される。"""
        store = ScheduleStore(store_path=store_path)
        task = ScheduledTask(cron="0 9 * * *", prompt="daily", durable=True)
        store.add(task)
        assert store.delete(task.id)
        assert store.count() == 0
        data = json.loads(store_path.read_text(encoding="utf-8"))
        assert data["tasks"] == []

    def test_delete_session_task(self, store_path: Path) -> None:
        """session-only タスクも削除できる。"""
        store = ScheduleStore(store_path=store_path)
        task = ScheduledTask(cron="*/5 * * * *", prompt="test", durable=False)
        store.add(task)
        assert store.delete(task.id)
        assert store.count() == 0

    def test_delete_nonexistent_returns_false(self, store_path: Path) -> None:
        """存在しないIDの削除は False を返す。"""
        store = ScheduleStore(store_path=store_path)
        assert not store.delete("sch_nonexistent")

    def test_max_jobs_limit(self, store_path: Path) -> None:
        """MAX_JOBS を超えると例外。"""
        store = ScheduleStore(store_path=store_path)
        for _ in range(MAX_JOBS):
            store.add(ScheduledTask(cron="*/5 * * * *", prompt="test", durable=False))
        with pytest.raises(ScheduleStoreError, match="Too many"):
            store.add(ScheduledTask(cron="*/5 * * * *", prompt="overflow", durable=False))

    def test_update_durable_task(self, store_path: Path) -> None:
        """durable タスクの更新が永続化される。"""
        store = ScheduleStore(store_path=store_path)
        task = ScheduledTask(cron="0 9 * * *", prompt="v1", durable=True)
        store.add(task)
        updated = ScheduledTask(
            id=task.id,
            cron=task.cron,
            prompt="v2",
            recurring=task.recurring,
            durable=task.durable,
            created_at=task.created_at,
        )
        store.update(updated)
        reloaded = ScheduleStore(store_path=store_path)
        got = reloaded.get(task.id)
        assert got is not None
        assert got.prompt == "v2"

    def test_update_nonexistent_raises(self, store_path: Path) -> None:
        """存在しないタスクの更新は例外。"""
        store = ScheduleStore(store_path=store_path)
        task = ScheduledTask(cron="*/5 * * * *", prompt="test", durable=False)
        with pytest.raises(ScheduleStoreError, match="not found"):
            store.update(task)

    def test_list_all_mixes_durable_and_session(self, store_path: Path) -> None:
        """list_all は durable と session を混ぜて返す。"""
        store = ScheduleStore(store_path=store_path)
        durable_task = ScheduledTask(cron="0 9 * * *", prompt="d", durable=True)
        session_task = ScheduledTask(cron="*/5 * * * *", prompt="s", durable=False)
        store.add(durable_task)
        store.add(session_task)
        ids = {t.id for t in store.list_all()}
        assert ids == {durable_task.id, session_task.id}

    def test_corrupted_file_raises(self, store_path: Path) -> None:
        """破損したJSONファイルは例外。"""
        store_path.parent.mkdir(parents=True, exist_ok=True)
        store_path.write_text("{invalid json", encoding="utf-8")
        with pytest.raises(ScheduleStoreError):
            ScheduleStore(store_path=store_path)

    def test_corrupted_entry_skipped(self, store_path: Path) -> None:
        """個別エントリの破損はスキップされる。"""
        store_path.parent.mkdir(parents=True, exist_ok=True)
        store_path.write_text(
            json.dumps(
                {
                    "tasks": [
                        {"id": "sch_broken"},  # required fields missing
                        {
                            "id": "sch_valid",
                            "cron": "0 9 * * *",
                            "prompt": "ok",
                            "recurring": True,
                            "durable": True,
                            "created_at": "2026-04-24T00:00:00+00:00",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        store = ScheduleStore(store_path=store_path)
        assert store.count() == 1
        assert store.get("sch_valid") is not None
