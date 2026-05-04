"""LLMプロバイダーの基底クラス。"""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

# 内部正規形式: OpenAI互換メッセージ形式
# role: "system" | "user" | "assistant" | "tool"
# tool_calls: OpenAI tool_call 形式のリスト（assistantターンのみ）
# tool_call_id: ツール結果メッセージのID（toolターンのみ）
# 各プロバイダーは _convert_messages() でこの形式から変換する
INTERNAL_MESSAGE_FORMAT = "openai-compatible"


@dataclass
class LLMUsage:
    """LLM トークン使用量。"""

    input_tokens: int
    output_tokens: int


@dataclass
class LLMResponse:
    """LLM応答。"""

    content: str
    tool_calls: list[dict[str, Any]] | None = None
    finish_reason: str = "stop"
    usage: LLMUsage | None = None


@dataclass
class LLMStreamChunk:
    """ストリーミングチャンク。"""

    content_delta: str = ""
    tool_calls_delta: list[dict[str, Any]] | None = None
    is_final: bool = False
    final_response: LLMResponse | None = None


class LLMProvider(ABC):
    """LLMプロバイダーの基底クラス。

    内部メッセージ形式はOpenAI互換形式を正規形式 (canonical format) として使用する。
    新しいプロバイダーを追加する場合は以下のメソッドをオーバーライドして
    プロバイダー固有の形式に変換すること:

    - _convert_messages(): メッセージリストの変換
    - _convert_tools(): ツール定義の変換
    """

    def _convert_messages(
        self, messages: list[dict[str, Any]]
    ) -> tuple[str, list[dict[str, Any]]]:
        """OpenAI互換メッセージをプロバイダー固有形式に変換する。

        デフォルト実装はOpenAI形式のままパススルーする（system_promptは空）。
        AnthropicやGemini等では必ずオーバーライドし、各APIが期待する形式に変換すること。

        Args:
            messages: OpenAI互換形式のメッセージリスト

        Returns:
            (system_prompt, converted_messages) のタプル。
            システムメッセージをAPIレベルのパラメータとして分離するプロバイダーは
            system_promptに設定し、messagesからは除外する。
        """
        return "", messages

    def _convert_tools(
        self, tools: list[dict[str, Any]] | None
    ) -> list[dict[str, Any]] | None:
        """OpenAI互換ツール定義をプロバイダー固有形式に変換する。

        デフォルト実装はそのままパススルーする。
        Anthropic等のOpenAI互換でないツール形式を持つプロバイダーはオーバーライドすること。

        Args:
            tools: OpenAI形式のツールリスト

        Returns:
            プロバイダー固有形式のツールリスト
        """
        return tools

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        """チャット補完を実行する。

        Args:
            messages: メッセージリスト
            tools: ツール定義リスト
            temperature: 温度パラメータ
            model: モデル名

        Returns:
            LLM応答
        """
        pass

    def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        model: str | None = None,
    ) -> Iterator[LLMStreamChunk]:
        """ストリーミングでチャット補完を実行する。

        Args:
            messages: メッセージリスト
            tools: ツール定義リスト
            temperature: 温度パラメータ
            model: モデル名

        Yields:
            ストリーミングチャンク

        Note:
            デフォルト実装は非ストリーミング（chat()を呼び出して一括返却）
            各プロバイダーで必要に応じてオーバーライドする
        """
        response = self.chat(messages, tools, temperature, model)
        yield LLMStreamChunk(
            content_delta=response.content,
            is_final=True,
            final_response=response,
        )
