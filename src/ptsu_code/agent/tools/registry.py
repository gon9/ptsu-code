"""ツールレジストリ - ツールの登録と管理。"""

from typing import Any

from ptsu_code.exceptions import PTSUError

from .base import Tool, ToolDefinition


class ToolRegistryError(PTSUError):
    """ツールレジストリエラー。"""


class ToolRegistry:
    """ツールレジストリ。"""

    def __init__(self) -> None:
        """初期化。"""
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """ツールを登録する。

        Args:
            tool: 登録するツール

        Raises:
            ToolRegistryError: 同名のツールが既に登録されている場合
        """
        name = tool.definition.name
        if name in self._tools:
            raise ToolRegistryError(f"Tool '{name}' is already registered", {"tool_name": name})
        self._tools[name] = tool

    def get(self, name: str) -> Tool | None:
        """ツールを取得する。

        Args:
            name: ツール名

        Returns:
            ツール。存在しない場合はNone
        """
        return self._tools.get(name)

    def get_all(self) -> tuple[Tool, ...]:
        """全てのツールを取得する。

        Returns:
            登録されている全ツール
        """
        return tuple(self._tools.values())

    def get_definitions(self) -> tuple[ToolDefinition, ...]:
        """全てのツール定義を取得する。

        Returns:
            登録されている全ツールの定義
        """
        return tuple(tool.definition for tool in self._tools.values())

    def get_openai_schemas(self) -> list[dict[str, Any]]:
        """OpenAI Function Calling用のスキーマを取得する。

        Returns:
            OpenAI Function Calling形式のスキーマリスト
        """
        return [tool.definition.to_openai_schema() for tool in self._tools.values()]

    def execute(self, name: str, **kwargs: Any) -> Any:
        """ツールを実行する。

        Args:
            name: ツール名
            **kwargs: ツールパラメータ

        Returns:
            実行結果

        Raises:
            ToolRegistryError: ツールが見つからない場合
        """
        tool = self.get(name)
        if tool is None:
            raise ToolRegistryError(f"Tool '{name}' not found", {"tool_name": name})

        tool.validate_parameters(**kwargs)
        return tool.execute(**kwargs)

    def clear(self) -> None:
        """全てのツールを削除する。"""
        self._tools.clear()

    def __len__(self) -> int:
        """登録されているツールの数を返す。

        Returns:
            ツール数
        """
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """ツールが登録されているか確認する。

        Args:
            name: ツール名

        Returns:
            登録されている場合True
        """
        return name in self._tools
