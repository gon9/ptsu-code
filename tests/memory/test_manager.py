"""SessionMemoryManager のユニットテスト。"""

from unittest.mock import MagicMock

import pytest

from ptsu_code.agent.providers.base import LLMResponse
from ptsu_code.memory.manager import SessionMemoryManager
from ptsu_code.memory.models import SessionMemoryConfig
from ptsu_code.memory.template import DEFAULT_TEMPLATE, REQUIRED_SECTIONS


def _make_valid_memory() -> str:
    """テスト用の有効なメモリ内容を生成する。"""
    lines = []
    for section in REQUIRED_SECTIONS:
        lines.append(section)
        lines.append("_placeholder description_")
        lines.append("content for this section")
        lines.append("")
    return "\n".join(lines)


@pytest.fixture()
def mock_provider() -> MagicMock:
    """モック LLM プロバイダー。"""
    provider = MagicMock()
    provider.chat.return_value = LLMResponse(content=_make_valid_memory())
    return provider


@pytest.fixture()
def small_config() -> SessionMemoryConfig:
    """テスト用に閾値を小さくした設定。"""
    return SessionMemoryConfig(
        minimum_tokens_to_init=10,
        minimum_tokens_between_update=5,
        tool_calls_between_updates=1,
    )


@pytest.fixture()
def manager(mock_provider, small_config, tmp_path) -> SessionMemoryManager:
    """テスト用マネージャー。"""
    return SessionMemoryManager(
        provider=mock_provider,
        session_id="20260429_120000",
        data_dir=tmp_path,
        config=small_config,
    )


class TestSessionMemoryManagerBasic:
    """基本動作のテスト。"""

    def test_initial_extraction_count_is_zero(self, manager) -> None:
        """初期状態で extraction_count が 0。"""
        assert manager.extraction_count == 0

    def test_add_turn_updates_state(self, manager) -> None:
        """add_turn が state を更新すること。"""
        manager.add_turn("hello", "world", tool_call_count=2)
        assert len(manager.state.conversation) == 1
        assert manager.state.tool_calls_since_last_extraction == 2

    def test_load_previous_returns_none_when_no_file(self, manager) -> None:
        """ファイルが存在しない場合 None を返すこと。"""
        assert manager.load_previous() is None

    def test_load_previous_returns_none_when_template_only(self, manager) -> None:
        """テンプレートのみの場合 None を返すこと。"""
        manager.storage.save(DEFAULT_TEMPLATE)
        assert manager.load_previous() is None

    def test_load_previous_returns_content_when_has_data(self, manager) -> None:
        """実際の内容がある場合は文字列を返すこと。"""
        manager.storage.save("# Session Title\nreal info here")
        result = manager.load_previous()
        assert result == "# Session Title\nreal info here"


class TestSessionMemoryManagerExtract:
    """抽出ロジックのテスト。"""

    def test_maybe_extract_false_below_threshold(self, manager) -> None:
        """閾値未満では maybe_extract が False を返すこと。"""
        manager.add_turn("x", "y")
        assert manager.maybe_extract() is False

    def test_maybe_extract_true_above_threshold(self, manager) -> None:
        """閾値を超えたら maybe_extract が True を返すこと。"""
        manager.add_turn("a" * 50, "b" * 50)
        assert manager.maybe_extract() is True

    def test_maybe_extract_increments_count(self, manager) -> None:
        """maybe_extract が成功したら extraction_count が増えること。"""
        manager.add_turn("a" * 50, "b" * 50)
        manager.maybe_extract()
        assert manager.extraction_count == 1

    def test_maybe_extract_saves_to_storage(self, manager) -> None:
        """maybe_extract がストレージに保存すること。"""
        manager.add_turn("a" * 50, "b" * 50)
        manager.maybe_extract()
        assert manager.storage.exists()

    def test_force_extract_returns_false_when_no_conversation(self, manager) -> None:
        """会話なしで force_extract は False を返すこと。"""
        assert manager.force_extract() is False

    def test_force_extract_true_with_conversation(self, manager) -> None:
        """会話があれば force_extract は True を返すこと。"""
        manager.add_turn("any", "message")
        assert manager.force_extract() is True

    def test_force_extract_saves_regardless_of_threshold(self, manager) -> None:
        """閾値未満でも force_extract は保存すること。"""
        manager.add_turn("short", "msg")
        manager.force_extract()
        assert manager.storage.exists()


class TestSessionMemoryManagerFinalize:
    """finalize のテスト。"""

    def test_finalize_archives_session(self, manager) -> None:
        """finalize がアーカイブを作成すること。"""
        manager.add_turn("some work", "done")
        manager.finalize()
        archive_path = manager.storage.archive_dir / "20260429_120000.md"
        assert archive_path.exists()

    def test_finalize_no_archive_when_no_conversation(self, manager) -> None:
        """会話なしで finalize してもアーカイブが作成されないこと。"""
        manager.finalize()
        assert not manager.storage.archive_dir.exists()

    def test_finalize_calls_force_extract(self, manager) -> None:
        """finalize が force_extract を呼ぶこと（会話が保存されること）。"""
        manager.add_turn("task", "done")
        manager.finalize()
        assert manager.extraction_count == 1
