"""スケジューラデーモン。

バックグラウンドスレッドで定期的にストアをチェックし、
発火すべきタスクをキューに追加する。
"""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ptsu_code.scheduler.cron_utils import compute_jitter_seconds, next_fire_time
from ptsu_code.scheduler.idle import IdleTracker
from ptsu_code.scheduler.models import ScheduledTask
from ptsu_code.scheduler.storage import ScheduleStore

DEFAULT_TICK_INTERVAL_SECONDS = 30.0
FIRE_WINDOW_SECONDS = 60  # tick間隔より広めに取ることで取りこぼしを防ぐ


@dataclass(frozen=True)
class FireEvent:
    """発火イベント。

    Attributes:
        task_id: 発火したタスクのID
        prompt: エージェントに渡すプロンプト
        fired_at: 発火時刻(UTC)
    """

    task_id: str
    prompt: str
    fired_at: datetime


TimeProvider = Callable[[], datetime]


def _default_now() -> datetime:
    """現在時刻(naive local)を返す。croniterはnaive datetimeで動作。"""
    return datetime.now()


class SchedulerDaemon:
    """スケジューラバックグラウンドスレッド。

    `start()` で起動、`stop()` で停止。発火したタスクは
    `fire_queue` に `FireEvent` として積まれる。
    CLI側が `fire_queue.get(timeout=...)` で取得する想定。
    """

    def __init__(
        self,
        store: ScheduleStore,
        idle_tracker: IdleTracker,
        tick_interval: float = DEFAULT_TICK_INTERVAL_SECONDS,
        time_provider: TimeProvider | None = None,
    ) -> None:
        """初期化する。

        Args:
            store: スケジュールストア
            idle_tracker: アイドル状態トラッカー
            tick_interval: tick間隔(秒)
            time_provider: テスト用の時刻供給関数 (naive local datetime)
        """
        self._store = store
        self._idle = idle_tracker
        self._tick_interval = tick_interval
        self._now = time_provider or _default_now
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.fire_queue: queue.Queue[FireEvent] = queue.Queue()

    def start(self) -> None:
        """バックグラウンドスレッドを起動する。"""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="ptsu-scheduler")
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        """スレッドを停止する。"""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    def _run(self) -> None:
        """スレッドのメインループ。"""
        while not self._stop_event.is_set():
            try:
                self.tick()
            except Exception:
                # デーモンを止めないため例外は握りつぶすが、
                # 本番では logging に記録すべき。
                pass
            if self._stop_event.wait(timeout=self._tick_interval):
                break

    def tick(self) -> list[FireEvent]:
        """1回分のチェックを実行する。

        テストから直接呼び出せるようにpublicにしてある。

        Returns:
            今回発火したイベントのリスト
        """
        fired: list[FireEvent] = []
        if not self._idle.is_idle():
            return fired
        now = self._now()
        for task in list(self._store.list_all()):
            if task.is_expired(now.replace(tzinfo=UTC) if now.tzinfo is None else now):
                self._store.delete(task.id)
                continue
            event = self._maybe_fire(task, now)
            if event is not None:
                fired.append(event)
                self.fire_queue.put(event)
        return fired

    def _maybe_fire(self, task: ScheduledTask, now: datetime) -> FireEvent | None:
        """タスクが発火時刻を過ぎているかを判定し、発火処理を行う。"""
        # last_fired_at を基点にするとrecurring が適切に動作する
        base = self._base_time(task, now)
        jitter = compute_jitter_seconds(task.cron)
        target = next_fire_time(task.cron, base=base, jitter_seconds=jitter)
        if target is None:
            return None
        if now < target:
            return None
        # 発火
        fired_at_iso = now.astimezone(UTC).isoformat() if now.tzinfo else now.replace(tzinfo=UTC).isoformat()
        if task.recurring:
            updated = ScheduledTask(
                id=task.id,
                cron=task.cron,
                prompt=task.prompt,
                recurring=task.recurring,
                durable=task.durable,
                created_at=task.created_at,
                last_fired_at=fired_at_iso,
                expires_at=task.expires_at,
            )
            self._store.update(updated)
        else:
            self._store.delete(task.id)
        return FireEvent(
            task_id=task.id,
            prompt=task.prompt,
            fired_at=now if now.tzinfo else now.replace(tzinfo=UTC),
        )

    def _base_time(self, task: ScheduledTask, now: datetime) -> datetime:
        """次回発火計算のための基準時刻を返す。

        last_fired_at があればそれ、なければ created_at の1分前(初回発火保証)。
        """
        if task.last_fired_at:
            dt = datetime.fromisoformat(task.last_fired_at)
            if dt.tzinfo is not None and now.tzinfo is None:
                dt = dt.replace(tzinfo=None)
            return dt
        # 初回発火: created_at を基準にして、次のcronマッチを計算する。
        # croniterのget_nextは「基準より厳密に未来」を返すので、作成直後に
        # 誤発火することはない。
        try:
            created = datetime.fromisoformat(task.created_at)
            if created.tzinfo is not None and now.tzinfo is None:
                created = created.replace(tzinfo=None)
            return created
        except ValueError:
            return now - timedelta(minutes=1)
