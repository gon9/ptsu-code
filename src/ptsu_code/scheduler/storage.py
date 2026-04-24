"""スケジュールタスクの永続化ストレージ。

Claude Codeの .claude/scheduled_tasks.json に相当するJSONストアと、
session-onlyなインメモリストアを統合管理する。
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path

from ptsu_code.scheduler.models import ScheduledTask

MAX_JOBS = 50
DEFAULT_STORE_FILENAME = "scheduled_tasks.json"
DEFAULT_STORE_DIR = ".ptsu"


class ScheduleStoreError(Exception):
    """スケジュールストアのエラー。"""


class ScheduleStore:
    """スケジュールタスクのストア(永続化 + インメモリ)。

    durable=True のタスクはJSONファイルに書き込まれ、
    durable=False はプロセス内のメモリに保持される。
    """

    def __init__(self, store_path: Path | None = None) -> None:
        """初期化する。

        Args:
            store_path: 永続化ファイルパス、省略時は `./.ptsu/scheduled_tasks.json`
        """
        self._store_path = store_path or Path.cwd() / DEFAULT_STORE_DIR / DEFAULT_STORE_FILENAME
        self._session_tasks: dict[str, ScheduledTask] = {}
        self._lock = threading.RLock()
        self._durable_tasks: dict[str, ScheduledTask] = {}
        self._load_durable()

    @property
    def store_path(self) -> Path:
        """永続化ファイルのパスを返す。"""
        return self._store_path

    def _load_durable(self) -> None:
        """永続化ファイルからdurableタスクを読み込む。"""
        if not self._store_path.exists():
            return
        try:
            data = json.loads(self._store_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            raise ScheduleStoreError(f"Failed to load {self._store_path}: {e}") from e
        tasks_data = data.get("tasks", [])
        for item in tasks_data:
            try:
                task = ScheduledTask.from_dict(item)
                self._durable_tasks[task.id] = task
            except (ValueError, KeyError):
                # 破損したエントリはスキップ
                continue

    def _persist(self) -> None:
        """durableタスクをJSONファイルに書き込む(atomic write)。"""
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "tasks": [task.to_dict() for task in self._durable_tasks.values()],
        }
        # tempfile で atomic write
        tmp_dir = self._store_path.parent
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(tmp_dir),
            delete=False,
            suffix=".tmp",
        ) as tmp:
            json.dump(payload, tmp, indent=2, ensure_ascii=False)
            tmp_name = tmp.name
        os.replace(tmp_name, self._store_path)

    def add(self, task: ScheduledTask) -> ScheduledTask:
        """タスクを追加する。

        Args:
            task: 追加するタスク

        Returns:
            追加されたタスク

        Raises:
            ScheduleStoreError: MAX_JOBSを超える場合
        """
        with self._lock:
            total = len(self._durable_tasks) + len(self._session_tasks)
            if total >= MAX_JOBS:
                raise ScheduleStoreError(
                    f"Too many scheduled jobs (max {MAX_JOBS}). Cancel one first."
                )
            if task.durable:
                self._durable_tasks[task.id] = task
                self._persist()
            else:
                self._session_tasks[task.id] = task
            return task

    def get(self, task_id: str) -> ScheduledTask | None:
        """IDでタスクを取得する。"""
        with self._lock:
            return self._durable_tasks.get(task_id) or self._session_tasks.get(task_id)

    def delete(self, task_id: str) -> bool:
        """タスクを削除する。

        Args:
            task_id: 削除するタスクID

        Returns:
            削除に成功した場合True
        """
        with self._lock:
            if task_id in self._durable_tasks:
                del self._durable_tasks[task_id]
                self._persist()
                return True
            if task_id in self._session_tasks:
                del self._session_tasks[task_id]
                return True
            return False

    def list_all(self) -> list[ScheduledTask]:
        """全タスクのリストを返す(durable + session)。"""
        with self._lock:
            return list(self._durable_tasks.values()) + list(self._session_tasks.values())

    def update(self, task: ScheduledTask) -> None:
        """既存タスクを更新する。

        Args:
            task: 更新後のタスク

        Raises:
            ScheduleStoreError: タスクが存在しない場合
        """
        with self._lock:
            if task.id in self._durable_tasks:
                self._durable_tasks[task.id] = task
                self._persist()
            elif task.id in self._session_tasks:
                self._session_tasks[task.id] = task
            else:
                raise ScheduleStoreError(f"Task {task.id} not found")

    def count(self) -> int:
        """タスクの総数を返す。"""
        with self._lock:
            return len(self._durable_tasks) + len(self._session_tasks)
