"""ツールの基底クラスと抽象化。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolParameter:
    """ツールパラメータの定義。"""

    name: str
    type: str
    description: str
    required: bool = True


@dataclass(frozen=True)
class ToolDefinition:
    """ツール定義。"""

    name: str
    description: str
    parameters: tuple[ToolParameter, ...]

    def to_openai_schema(self) -> dict[str, Any]:
        """OpenAI Function Calling用のスキーマに変換する。

        Returns:
            OpenAI Function Calling形式のスキーマ
        """
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description,
            }
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


@dataclass(frozen=True)
class ToolResult:
    """ツール実行結果。"""

    success: bool
    output: str
    error: str | None = None


class Tool(ABC):
    """ツールの基底クラス。"""

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """ツール定義を返す。

        Returns:
            ツール定義
        """
        pass

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """ツールを実行する。

        Args:
            **kwargs: ツールパラメータ

        Returns:
            実行結果
        """
        pass

    def validate_parameters(self, **kwargs: Any) -> None:
        """パラメータのバリデーションを行う。

        Args:
            **kwargs: ツールパラメータ

        Raises:
            ValueError: 必須パラメータが不足している場合
        """
        required_params = {p.name for p in self.definition.parameters if p.required}
        provided_params = set(kwargs.keys())
        missing_params = required_params - provided_params

        if missing_params:
            raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
