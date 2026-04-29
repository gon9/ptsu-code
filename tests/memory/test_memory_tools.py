"""MemorySummaryTool のユニットテスト。"""

from unittest.mock import MagicMock

import pytest

from ptsu_code.agent.providers.base import LLMResponse
from ptsu_code.agent.tools.memory_tools import MemorySummaryTool
from ptsu_code.memory.manager import SessionMemoryManager
from ptsu_code.memory.models import SessionMemoryConfig
from ptsu_code.memory.template import REQUIRED_SECTIONS


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
def manager(mock_provider, tmp_path) -> SessionMemoryManager:
    """テスト用マネージャー（閾値を小さく設定）。"""
    return SessionMemoryManager(
        provider=mock_provider,
        session_id="20260430_070000",
        data_dir=tmp_path,
        config=SessionMemoryConfig(
            minimum_tokens_to_init=10,
            minimum_tokens_between_update=5,
            tool_calls_between_updates=1,
        ),
    )


class TestMemorySummaryTool:
    """MemorySummaryTool のテスト。"""

    def test_definition_name(self, manager) -> None:
        """ツール名が memory_summary であること。"""
        tool = MemorySummaryTool(manager)
        assert tool.definition.name == "memory_summary"

    def test_definition_has_no_parameters(self, manager) -> None:
        """パラメータなしのツールであること。"""
        tool = MemorySummaryTool(manager)
        assert len(tool.definition.parameters) == 0

    def test_execute_success_with_conversation(self, manager) -> None:
        """会話がある場合 execute が成功すること。"""
        manager.add_turn("user message", "assistant response")
        tool = MemorySummaryTool(manager)
        result = tool.execute()
        assert result.success is True
        assert "Session memory saved" in result.output

    def test_execute_success_includes_path(self, manager) -> None:
        """execute の出力にファイルパスが含まれること。"""
        manager.add_turn("user message", "assistant response")
        tool = MemorySummaryTool(manager)
        result = tool.execute()
        assert str(manager.storage.current_path) in result.output

    def test_execute_fails_when_no_conversation(self, manager) -> None:
        """会話がない場合 execute が失敗を返すこと。"""
        tool = MemorySummaryTool(manager)
        result = tool.execute()
        assert result.success is False
        assert "No conversation" in result.output
        assert result.error is not None

    def test_execute_saves_to_storage(self, manager) -> None:
        """execute 後にストレージにファイルが存在すること。"""
        manager.add_turn("some work", "done")
        tool = MemorySummaryTool(manager)
        tool.execute()
        assert manager.storage.exists()
