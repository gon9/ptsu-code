"""Agent実行ランタイム。"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from ptsu_code.config import settings
from ptsu_code.exceptions import PTSUError

from .approval import ApprovalManager
from .providers.anthropic_provider import AnthropicProvider
from .providers.base import LLMProvider, LLMStreamChunk
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
    approval_manager: ApprovalManager = field(default_factory=ApprovalManager)
    model: str | None = None
    max_turns: int = 10
    temperature: float | None = None

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
        self.provider: LLMProvider

        if self.provider_name == "anthropic":
            api_key = api_key or settings.anthropic_api_key
            if not api_key:
                raise RuntimeError(
                    "Anthropic API key is not configured",
                    {"config_key": "anthropic_api_key"},
                )
            self.provider = AnthropicProvider(
                api_key=api_key,
                default_model=model or settings.anthropic_model,
            )
        else:
            api_key = api_key or settings.openai_api_key
            if not api_key:
                raise RuntimeError(
                    "OpenAI API key is not configured",
                    {"config_key": "openai_api_key"},
                )
            self.provider = OpenAIProvider(
                api_key=api_key,
                default_model=model or settings.openai_model,
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

            response = self.provider.chat(
                messages=session.get_messages(),
                tools=tools,
                temperature=session.temperature,
                model=session.model,
            )

            return response

        except Exception as e:
            raise RuntimeError(f"Failed to run turn: {e}", {"provider": self.provider_name}) from e

    def run_turn_stream(self, session: AgentSession) -> Iterator[LLMStreamChunk]:
        """ターンをストリーミングで実行する。

        Args:
            session: エージェントセッション

        Yields:
            ストリーミングチャンク

        Raises:
            RuntimeError: ターン実行に失敗した場合
        """
        try:
            messages = [msg.to_dict() for msg in session.messages]
            tools = session.tool_registry.get_openai_schemas()

            yield from self.provider.stream(
                messages=messages,
                tools=tools,
                temperature=session.temperature,
                model=session.model,
            )

        except Exception as e:
            raise RuntimeError(f"Failed to run turn stream: {e}", {"provider": self.provider_name}) from e

    def execute_tool_calls(
        self,
        session: AgentSession,
        tool_calls: list[dict[str, Any]],
        request_approval_callback: Any = None,
        show_progress_callback: Any = None,
    ) -> list[Message]:
        """ツール呼び出しを実行する。

        Args:
            session: エージェントセッション
            tool_calls: ツール呼び出しリスト
            request_approval_callback: 承認を求めるコールバック関数
            show_progress_callback: 進捗を表示するコールバック関数

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

                # 承認チェック
                tool = session.tool_registry.get(function_name)
                if tool and session.approval_manager.needs_approval(
                    function_name, tool.requires_approval
                ):
                    # 承認を求める
                    if request_approval_callback:
                        decision = request_approval_callback(function_name, args)

                        if decision == "n":
                            # 拒否された
                            results.append(
                                Message(
                                    role="tool",
                                    content="Tool execution rejected by user",
                                    tool_call_id=tool_call["id"],
                                    name=function_name,
                                )
                            )
                            continue
                        elif decision == "a":
                            # 常に承認
                            session.approval_manager.add_auto_approved_tool(function_name)
                    else:
                        # コールバックがない場合は拒否
                        results.append(
                            Message(
                                role="tool",
                                content="Tool execution requires approval but no callback provided",
                                tool_call_id=tool_call["id"],
                                name=function_name,
                            )
                        )
                        continue

                # 進捗表示
                if show_progress_callback:
                    show_progress_callback(function_name, args, "executing")

                # ツール実行
                result = session.tool_registry.execute(function_name, **args)

                # 結果表示
                if show_progress_callback:
                    show_progress_callback(
                        function_name,
                        args,
                        "completed",
                        success=result.success,
                        output=result.output,
                        error=result.error,
                    )

                raw_content = str(result.output if result.success else result.error)
                if len(raw_content) > 2000:
                    raw_content = raw_content[:1900] + f"\n... (truncated, {len(raw_content)} chars total)"
                results.append(
                    Message(
                        role="tool",
                        content=raw_content,
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

    def run_loop(
        self,
        session: AgentSession,
        user_message: str,
        request_approval_callback: Any = None,
        show_progress_callback: Any = None,
    ) -> str:
        """会話ループを実行する。

        Args:
            session: エージェントセッション
            user_message: ユーザーメッセージ
            request_approval_callback: 承認を求めるコールバック関数
            show_progress_callback: 進捗を表示するコールバック関数

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

                tool_results = self.execute_tool_calls(
                    session,
                    response.tool_calls,
                    request_approval_callback,
                    show_progress_callback,
                )

                for result in tool_results:
                    session.messages.append(result)

            else:
                session.add_message("assistant", response.content)
                return response.content

        raise RuntimeError(
            f"Maximum turns ({session.max_turns}) exceeded without completion",
            {"turns": session.max_turns},
        )

    def run_loop_stream(
        self,
        session: AgentSession,
        user_message: str,
        request_approval_callback: Any = None,
        show_progress_callback: Any = None,
        stream_callback: Any = None,
    ) -> str:
        """会話ループをストリーミングで実行する。

        Args:
            session: エージェントセッション
            user_message: ユーザーメッセージ
            request_approval_callback: 承認を求めるコールバック関数
            show_progress_callback: 進捗を表示するコールバック関数
            stream_callback: ストリーミングチャンクを処理するコールバック関数

        Returns:
            アシスタントの最終応答

        Raises:
            RuntimeError: 最大ターン数を超えた場合
        """
        session.add_message("user", user_message)

        for turn in range(session.max_turns):
            # ストリーミング開始を通知
            if stream_callback:
                stream_callback("start")

            final_response = None
            for chunk in self.run_turn_stream(session):
                # コンテンツチャンクを通知
                if chunk.content_delta and stream_callback:
                    stream_callback("chunk", chunk.content_delta)

                # 最終チャンク
                if chunk.is_final and chunk.final_response:
                    final_response = chunk.final_response

            # ストリーミング終了を通知
            if stream_callback:
                stream_callback("end")

            if not final_response:
                raise RuntimeError("No final response received from stream")

            if final_response.tool_calls:
                session.add_message(
                    "assistant",
                    final_response.content,
                    tool_calls=final_response.tool_calls,
                )

                tool_results = self.execute_tool_calls(
                    session,
                    final_response.tool_calls,
                    request_approval_callback,
                    show_progress_callback,
                )

                for result in tool_results:
                    session.messages.append(result)

            else:
                session.add_message("assistant", final_response.content)
                return final_response.content

        raise RuntimeError(
            f"Maximum turns ({session.max_turns}) exceeded without completion",
            {"turns": session.max_turns},
        )
