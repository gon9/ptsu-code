"""IdleTracker のテスト。"""

from ptsu_code.scheduler.idle import IdleTracker


class TestIdleTracker:
    """IdleTracker のテスト。"""

    def test_initial_state_is_busy(self) -> None:
        """初期状態は busy (is_idle=False)。"""
        tracker = IdleTracker()
        assert not tracker.is_idle()

    def test_set_idle_true(self) -> None:
        """set_idle(True) でアイドルになる。"""
        tracker = IdleTracker()
        tracker.set_idle(True)
        assert tracker.is_idle()

    def test_set_idle_toggle(self) -> None:
        """True/False を切り替えられる。"""
        tracker = IdleTracker()
        tracker.set_idle(True)
        assert tracker.is_idle()
        tracker.set_idle(False)
        assert not tracker.is_idle()
