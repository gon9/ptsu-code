"""システムプロンプトとプロンプトテンプレート。"""

from typing import Any


class SystemPrompts:
    """システムプロンプトのコレクション。"""

    @staticmethod
    def coding_assistant() -> str:
        """コーディングアシスタント用のシステムプロンプト。

        Returns:
            システムプロンプト
        """
        return """You are PTSU, an AI coding assistant with access to powerful tools.

## Your Capabilities

You have access to the following tools:
- **read_file**: Read file contents
- **write_file**: Write or modify files (requires user approval)
- **execute_command**: Run shell commands (requires user approval)
- **grep_search**: Search file contents with regex patterns
- **find_files**: Find files by name or pattern
- **list_directory**: List directory contents

## Guidelines

1. **Be Proactive**: Use tools to gather information before answering
2. **Be Precise**: Read relevant files before making changes
3. **Be Safe**: Destructive operations require user approval
4. **Be Efficient**: Use search tools to explore the codebase
5. **Be Clear**: Explain what you're doing and why

## Tool Usage Best Practices

- Use `grep_search` or `find_files` to locate relevant code
- Use `read_file` to understand context before modifying **existing** files
- Use `list_directory` to explore project structure when needed
- When asked to **create a new file**, call `write_file` directly without exploring first
- When asked to **modify an existing file**, read it first to understand context
- Provide clear commit messages for code changes

## Response Style

- Be concise and direct
- Show code snippets when relevant
- Explain your reasoning briefly
- Ask for clarification when needed

Help the user accomplish their coding tasks efficiently and safely."""

    @staticmethod
    def with_context(base_prompt: str, context: dict[str, Any]) -> str:
        """コンテキストを追加したプロンプトを生成する。

        Args:
            base_prompt: ベースプロンプト
            context: コンテキスト情報

        Returns:
            コンテキスト付きプロンプト
        """
        context_parts = []

        if "project_info" in context:
            context_parts.append(f"\n## Project Context\n{context['project_info']}")

        if "current_task" in context:
            context_parts.append(f"\n## Current Task\n{context['current_task']}")

        if "constraints" in context:
            context_parts.append(f"\n## Constraints\n{context['constraints']}")

        if context_parts:
            return base_prompt + "\n" + "\n".join(context_parts)

        return base_prompt


class PromptTemplates:
    """プロンプトテンプレートのコレクション。"""

    @staticmethod
    def code_review_request(file_path: str, focus: str | None = None) -> str:
        """コードレビューリクエストのプロンプト。

        Args:
            file_path: レビュー対象ファイルパス
            focus: レビューの焦点（オプション）

        Returns:
            プロンプト
        """
        prompt = f"Please review the code in `{file_path}`."
        if focus:
            prompt += f" Focus on: {focus}"
        return prompt

    @staticmethod
    def bug_fix_request(description: str, file_path: str | None = None) -> str:
        """バグ修正リクエストのプロンプト。

        Args:
            description: バグの説明
            file_path: 関連ファイルパス（オプション）

        Returns:
            プロンプト
        """
        prompt = f"There's a bug: {description}"
        if file_path:
            prompt += f" in `{file_path}`"
        prompt += ". Please investigate and fix it."
        return prompt

    @staticmethod
    def feature_request(description: str, requirements: list[str] | None = None) -> str:
        """機能追加リクエストのプロンプト。

        Args:
            description: 機能の説明
            requirements: 要件リスト（オプション）

        Returns:
            プロンプト
        """
        prompt = f"Please implement the following feature: {description}"
        if requirements:
            prompt += "\n\nRequirements:\n"
            prompt += "\n".join(f"- {req}" for req in requirements)
        return prompt

    @staticmethod
    def refactoring_request(target: str, goal: str) -> str:
        """リファクタリングリクエストのプロンプト。

        Args:
            target: リファクタリング対象
            goal: リファクタリングの目的

        Returns:
            プロンプト
        """
        return f"Please refactor {target} to {goal}."

    @staticmethod
    def test_generation_request(target: str, test_type: str = "unit") -> str:
        """テスト生成リクエストのプロンプト。

        Args:
            target: テスト対象
            test_type: テストタイプ（unit, integration, e2e）

        Returns:
            プロンプト
        """
        return f"Please generate {test_type} tests for {target}."
