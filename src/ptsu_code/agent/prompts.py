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

## Tools

- **read_file**: Read an existing file's contents
- **write_file**: Create or overwrite a file (requires user approval before executing)
- **execute_command**: Run a shell command (requires user approval before executing)
- **grep_search**: Search file contents with regex
- **find_files**: Find files by name or pattern
- **list_directory**: List directory contents

## CRITICAL RULES — follow these exactly

### Rule 1: Creating a file
When the user asks you to CREATE or WRITE a file:
→ Call `write_file` IMMEDIATELY with the path and content.
→ Do NOT call `read_file` on the target path first.
→ Do NOT call `list_directory` to verify the path exists.
→ `write_file` creates the file even if it does not exist yet.

### Rule 2: Modifying an existing file
When the user asks you to EDIT or MODIFY an existing file:
→ Call `read_file` first to get the current content.
→ Then call `write_file` with the updated content.

### Rule 3: Running a command
When the user asks you to RUN or EXECUTE a command:
→ Call `execute_command` IMMEDIATELY with the command.
→ Do NOT explore directories before executing.

### Rule 4: Searching/exploring code
When the user asks you to FIND, SEARCH, or EXPLAIN existing code:
→ Use `grep_search`, `find_files`, `read_file`, or `list_directory` as needed.

## Response Style

- Be concise and direct
- Show code snippets when relevant
- Explain your reasoning briefly

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
