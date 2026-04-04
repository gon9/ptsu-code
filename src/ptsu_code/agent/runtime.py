"""Agent実行ランタイム。"""

from dataclasses import dataclass, field
from typing import Any

from ptsu_code.config import settings
from ptsu_code.exceptions import PTSUError

from .providers.anthropic_provider import AnthropicProvider
from .providers.base import LLMProvider
from .providers.openai_provider import OpenAIProvider
from .tools.registry import ToolRegistry


class RuntimeError(PTSUError):
    """ランタイムエラー。"""


@dataclass
class Message:
    """会話メッセージ。"""

    role: str
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換する。

        Returns:
            辞書形式のメッセージ
        """
        msg: dict[str, Any] = {
            "role": self.role,
            "content": self.content,
        }

        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls

        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id

        if self.name:
            msg["name"] = self.name

        return msg


@dataclass
class AgentSession:
    """エージェントセッション。"""

    messages: list[Message] = field(default_factory=list)
    tool_registry: ToolRegistry = field(default_factory=ToolRegistry)
    model: str | None = None
    max_turns: int = 10
    temperature: float = 0.7

    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        """メッセージを追加する。

        Args:
            role: メッセージの役割
            content: メッセージ内容
            **kwargs: その他のメッセージ属性
        """
        self.messages.append(Message(role=role, content=content, **kwargs))

    def get_messages(self) -> list[dict[str, Any]]:
        """メッセージリストを取得する。

        Returns:
            メッセージリスト
        """
        return [msg.to_dict() for msg in self.messages]


class AgentRuntime:
    """エージェント実行ランタイム。"""

    def __init__(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        """初期化。

        Args:
            provider: LLMプロバイダー ('openai' or 'anthropic')
            api_key: APIキー。Noneの場合は設定から取得
            model: モデル名
        """
        self.provider_name = provider or settings.llm_provider
        self.llm: LLMProvider

        if self.provider_name == "anthropic":
            api_key = api_key or settings.anthropic_api_key
            if not api_key:
                raise RuntimeError(
                    "Anthropic API key is not configured",
                    {"config_key": "anthropic_api_key"},
                )
            self.llm = AnthropicProvider(
                api_key=api_key,
                default_model=model or "claude-3-5-sonnet-20241022",
            )
        else:
            api_key = api_key or settings.openai_api_key
            if not api_key:
                raise RuntimeError(
                    "OpenAI API key is not configured",
                    {"config_key": "openai_api_key"},
                )
            self.llm = OpenAIProvider(
                api_key=api_key,
                default_model=model or "gpt-4o-mini",
            )

    def run_turn(self, session: AgentSession) -> Any:
        """1ターンの会話を実行する。

        Args:
            session: エージェントセッション

        Returns:
            LLMレスポンス

        Raises:
            RuntimeError: API呼び出しに失敗した場合
        """
        try:
            tools = session.tool_registry.get_openai_schemas() if len(session.tool_registry) > 0 else None

            response = self.llm.chat(
                messages=session.get_messages(),
                tools=tools,
                temperature=session.temperature,
                model=session.model,
            )

            return response

        except Exception as e:
            raise RuntimeError(f"Failed to run turn: {e}", {"provider": self.provider_name}) from e

    def execute_tool_calls(self, session: AgentSession, tool_calls: list[dict[str, Any]]) -> list[Message]:
        """ツール呼び出しを実行する。

        Args:
            session: エージェントセッション
            tool_calls: ツール呼び出しリスト

        Returns:
            ツール実行結果のメッセージリスト
        """
        results: list[Message] = []

        for tool_call in tool_calls:
            function_name = tool_call["function"]["name"]
            function_args = tool_call["function"]["arguments"]

            try:
                import json

                args = json.loads(function_args)
                result = session.tool_registry.execute(function_name, **args)

                results.append(
                    Message(
                        role="tool",
                        content=str(result.output if result.success else result.error),
                        tool_call_id=tool_call["id"],
                        name=function_name,
                    )
                )

            except Exception as e:
                results.append(
                    Message(
                        role="tool",
                        content=f"Error executing tool: {e}",
                        tool_call_id=tool_call["id"],
                        name=function_name,
                    )
                )

        return results

    def run_loop(self, session: AgentSession, user_message: str) -> str:
        """会話ループを実行する。

        Args:
            session: エージェントセッション
            user_message: ユーザーメッセージ

        Returns:
            アシスタントの最終応答

        Raises:
            RuntimeError: 最大ターン数を超えた場合
        """
        session.add_message("user", user_message)

        for turn in range(session.max_turns):
            response = self.run_turn(session)

            if response.tool_calls:
                session.add_message(
                    "assistant",
                    response.content,
                    tool_calls=response.tool_calls,
                )

                tool_results = self.execute_tool_calls(session, response.tool_calls)

                for result in tool_results:
                    session.messages.append(result)

            else:
                session.add_message("assistant", response.content)
                return response.content

        raise RuntimeError(
            f"Maximum turns ({session.max_turns}) exceeded without completion",
            {"max_turns": session.max_turns, "current_turn": turn},
        )
