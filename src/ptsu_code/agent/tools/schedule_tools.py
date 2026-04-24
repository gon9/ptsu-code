"""スケジュール関連ツール。

LLMがプロンプトを cron 式で未来の時刻にスケジュールするためのツール群。
Claude Code の CronCreateTool/CronDeleteTool/CronListTool に相当する。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from ptsu_code.agent.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult
from ptsu_code.scheduler.cron_utils import (
    cron_to_human,
    next_fire_time,
    validate_cron,
)
from ptsu_code.scheduler.models import ScheduledTask
from ptsu_code.scheduler.storage import ScheduleStore, ScheduleStoreError

DEFAULT_MAX_AGE_DAYS = 30


class ScheduleCreateTool(Tool):
    """プロンプトをcron式でスケジュール実行するツール。"""

    def __init__(self, store: ScheduleStore) -> None:
        """初期化する。

        Args:
            store: スケジュールストア
        """
        self._store = store

    @property
    def definition(self) -> ToolDefinition:
        """ツール定義を返す。"""
        return ToolDefinition(
            name="schedule_create",
            description=(
                "プロンプトを未来の時刻にスケジュール実行する。"
                "5-field cron式で繰り返し実行または一回限りの実行を指定できる。"
                "例: '0 9 * * 1-5'は平日9時に実行、'*/5 * * * *'は5分毎に実行。"
                f"recurring=trueはデフォルトで{DEFAULT_MAX_AGE_DAYS}日後に自動失効する。"
                "durable=trueでセッションをまたいで永続化される。"
            ),
            parameters=(
                ToolParameter(
                    name="cron",
                    type="string",
                    description=(
                        "5-field cron式 (M H DoM Mon DoW)。"
                        "例: '0 9 * * 1-5' (平日9時)、'*/5 * * * *' (5分毎)、"
                        "'30 14 28 2 *' (2月28日14時30分)"
                    ),
                    required=True,
                ),
                ToolParameter(
                    name="prompt",
                    type="string",
                    description="発火時にエージェントへ渡すプロンプト",
                    required=True,
                ),
                ToolParameter(
                    name="recurring",
                    type="boolean",
                    description="true(デフォ)=繰り返し実行、false=一回のみ実行",
                    required=False,
                ),
                ToolParameter(
                    name="durable",
                    type="boolean",
                    description=(
                        "true=.ptsu/scheduled_tasks.jsonに永続化、"
                        "false(デフォ)=セッション内のみ"
                    ),
                    required=False,
                ),
            ),
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        """スケジュールを作成する。"""
        try:
            self.validate_parameters(**kwargs)
            cron_expr = str(kwargs["cron"])
            prompt = str(kwargs["prompt"])
            recurring = bool(kwargs.get("recurring", True))
            durable = bool(kwargs.get("durable", False))

            if not validate_cron(cron_expr):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Invalid cron expression '{cron_expr}'. Expected 5 fields: M H DoM Mon DoW.",
                )
            if next_fire_time(cron_expr) is None:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Cron expression '{cron_expr}' does not match any valid time.",
                )

            expires_at: str | None = None
            if recurring:
                expires_dt = datetime.now(UTC) + timedelta(days=DEFAULT_MAX_AGE_DAYS)
                expires_at = expires_dt.isoformat()

            task = ScheduledTask(
                cron=cron_expr,
                prompt=prompt,
                recurring=recurring,
                durable=durable,
                expires_at=expires_at,
            )
            try:
                self._store.add(task)
            except ScheduleStoreError as e:
                return ToolResult(success=False, output="", error=str(e))

            human = cron_to_human(cron_expr)
            where = (
                "persisted to .ptsu/scheduled_tasks.json"
                if durable
                else "session-only (will be lost when ptsu exits)"
            )
            kind = "recurring" if recurring else "one-shot"
            expire_note = (
                f" Auto-expires in {DEFAULT_MAX_AGE_DAYS} days." if recurring else ""
            )
            return ToolResult(
                success=True,
                output=(
                    f"Scheduled {kind} task {task.id} ({human}). "
                    f"{where}.{expire_note} Use schedule_delete to cancel."
                ),
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to create schedule: {e}",
            )


class ScheduleListTool(Tool):
    """スケジュールされたタスクの一覧を返すツール。"""

    def __init__(self, store: ScheduleStore) -> None:
        """初期化する。"""
        self._store = store

    @property
    def definition(self) -> ToolDefinition:
        """ツール定義を返す。"""
        return ToolDefinition(
            name="schedule_list",
            description="スケジュールされたタスクの一覧を返す。durable/session-only 両方を含む。",
            parameters=(),
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        """タスク一覧を返す。"""
        try:
            tasks = self._store.list_all()
            if not tasks:
                return ToolResult(success=True, output="No scheduled tasks.")
            lines = []
            for t in tasks:
                kind = "recurring" if t.recurring else "one-shot"
                where = "durable" if t.durable else "session"
                human = cron_to_human(t.cron)
                last = f" last_fired={t.last_fired_at}" if t.last_fired_at else ""
                lines.append(
                    f"{t.id} [{kind}/{where}] cron='{t.cron}' ({human}) "
                    f"prompt={t.prompt!r}{last}"
                )
            return ToolResult(success=True, output="\n".join(lines))
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to list schedules: {e}",
            )


class ScheduleDeleteTool(Tool):
    """スケジュールされたタスクを削除するツール。"""

    def __init__(self, store: ScheduleStore) -> None:
        """初期化する。"""
        self._store = store

    @property
    def definition(self) -> ToolDefinition:
        """ツール定義を返す。"""
        return ToolDefinition(
            name="schedule_delete",
            description="スケジュールされたタスクを id 指定で削除する。",
            parameters=(
                ToolParameter(
                    name="id",
                    type="string",
                    description="削除するタスクID (schedule_list で確認可能)",
                    required=True,
                ),
            ),
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        """タスクを削除する。"""
        try:
            self.validate_parameters(**kwargs)
            task_id = str(kwargs["id"])
            if self._store.delete(task_id):
                return ToolResult(success=True, output=f"Deleted schedule {task_id}.")
            return ToolResult(
                success=False,
                output="",
                error=f"Schedule {task_id} not found.",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to delete schedule: {e}",
            )
