"""Sub-agentの基底クラスと共通データ構造。"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ptsu_code.agent.runtime import AgentRuntime


class AgentRole(Enum):
    """Sub-agentの役割。"""

    SEARCHER = "searcher"
    CODER = "coder"
    EXECUTOR = "executor"
    GENERAL = "general"


@dataclass
class SubAgentConfig:
    """Sub-agentの設定。"""

    role: AgentRole
    name: str
    description: str
    system_prompt: str
    allowed_tools: list[str] = field(default_factory=list)
    max_turns: int = 10
    temperature: float | None = None


class SubAgent(ABC):
    """Sub-agentの基底クラス。"""

    @property
    @abstractmethod
    def config(self) -> SubAgentConfig:
        """Sub-agentの設定を返す。"""

    @abstractmethod
    def run(
        self,
        runtime: "AgentRuntime",
        message: str,
        context: dict[str, Any] | None = None,
        request_approval_callback: Callable | None = None,
        show_progress_callback: Callable | None = None,
    ) -> str:
        """メッセージを処理して結果を返す。

        Args:
            runtime: AgentRuntimeインスタンス
            message: ユーザーメッセージ
            context: コンテキスト情報（オプション）
            request_approval_callback: ツール承認コールバック（オプション）
            show_progress_callback: 進捗表示コールバック（オプション）

        Returns:
            処理結果
        """
