"""REPLアイドル状態トラッカー。"""

from __future__ import annotations

import threading


class IdleTracker:
    """REPL のアイドル状態を管理する。

    Scheduler は is_idle() が True のときだけタスクを発火する。
    CLI 側で get_input() の前後に set_idle(True/False) を呼ぶ。
    """

    def __init__(self) -> None:
        """初期化(初期状態はbusy)。"""
        self._idle = False
        self._lock = threading.Lock()

    def set_idle(self, value: bool) -> None:
        """アイドル状態を設定する。"""
        with self._lock:
            self._idle = value

    def is_idle(self) -> bool:
        """現在アイドルかを返す。"""
        with self._lock:
            return self._idle
