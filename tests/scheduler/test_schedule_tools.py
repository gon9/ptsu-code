"""schedule_tools のテスト。"""

from pathlib import Path

import pytest

from ptsu_code.agent.tools.schedule_tools import (
    ScheduleCreateTool,
    ScheduleDeleteTool,
    ScheduleListTool,
)
from ptsu_code.scheduler.storage import ScheduleStore


@pytest.fixture
def store(tmp_path: Path) -> ScheduleStore:
    """一時 ScheduleStore を返す。"""
    return ScheduleStore(store_path=tmp_path / "tasks.json")


class TestScheduleCreateTool:
    """ScheduleCreateTool のテスト。"""

    def test_create_recurring(self, store: ScheduleStore) -> None:
        """recurring タスクを作成できる。"""
        tool = ScheduleCreateTool(store)
        result = tool.execute(cron="0 9 * * *", prompt="daily")
        assert result.success
        assert "recurring" in result.output
        assert store.count() == 1

    def test_create_one_shot(self, store: ScheduleStore) -> None:
        """one-shot タスクを作成できる。"""
        tool = ScheduleCreateTool(store)
        result = tool.execute(cron="0 9 * * *", prompt="once", recurring=False)
        assert result.success
        assert "one-shot" in result.output

    def test_create_durable(self, store: ScheduleStore) -> None:
        """durable タスクを作成できる。"""
        tool = ScheduleCreateTool(store)
        result = tool.execute(
            cron="0 9 * * *",
            prompt="keep",
            durable=True,
        )
        assert result.success
        assert "persisted" in result.output

    def test_invalid_cron_fails(self, store: ScheduleStore) -> None:
        """無効な cron 式は失敗する。"""
        tool = ScheduleCreateTool(store)
        result = tool.execute(cron="invalid cron", prompt="test")
        assert not result.success
        assert "Invalid cron" in (result.error or "")

    def test_missing_prompt_fails(self, store: ScheduleStore) -> None:
        """prompt 欠落は失敗する。"""
        tool = ScheduleCreateTool(store)
        result = tool.execute(cron="0 9 * * *")
        assert not result.success

    def test_recurring_has_expires_at(self, store: ScheduleStore) -> None:
        """recurring タスクは expires_at が設定される。"""
        tool = ScheduleCreateTool(store)
        tool.execute(cron="0 9 * * *", prompt="test")
        task = store.list_all()[0]
        assert task.expires_at is not None


class TestScheduleListTool:
    """ScheduleListTool のテスト。"""

    def test_empty_list(self, store: ScheduleStore) -> None:
        """空の時は No scheduled tasks を返す。"""
        tool = ScheduleListTool(store)
        result = tool.execute()
        assert result.success
        assert "No scheduled" in result.output

    def test_list_shows_tasks(self, store: ScheduleStore) -> None:
        """タスクが存在すれば一覧に表示される。"""
        create = ScheduleCreateTool(store)
        create.execute(cron="0 9 * * *", prompt="morning brief")
        list_tool = ScheduleListTool(store)
        result = list_tool.execute()
        assert result.success
        assert "morning brief" in result.output
        assert "sch_" in result.output


class TestScheduleDeleteTool:
    """ScheduleDeleteTool のテスト。"""

    def test_delete_existing(self, store: ScheduleStore) -> None:
        """存在するタスクを削除できる。"""
        create = ScheduleCreateTool(store)
        create.execute(cron="0 9 * * *", prompt="test")
        task_id = store.list_all()[0].id

        delete = ScheduleDeleteTool(store)
        result = delete.execute(id=task_id)
        assert result.success
        assert store.count() == 0

    def test_delete_nonexistent_fails(self, store: ScheduleStore) -> None:
        """存在しないタスクの削除は失敗する。"""
        delete = ScheduleDeleteTool(store)
        result = delete.execute(id="sch_nonexistent")
        assert not result.success
        assert "not found" in (result.error or "")

    def test_missing_id_fails(self, store: ScheduleStore) -> None:
        """id 欠落は失敗する。"""
        delete = ScheduleDeleteTool(store)
        result = delete.execute()
        assert not result.success
