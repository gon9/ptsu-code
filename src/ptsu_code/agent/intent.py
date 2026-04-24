"""ユーザー入力のIntent分類器。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ptsu_code.agent.providers.base import LLMProvider

from ptsu_code.agent.sub_agents.base import AgentRole

_INTENT_PROMPT = """Classify the user's intent into one of the following categories:

**SEARCH**: User wants to find, explore, or understand existing code
Examples:
- "Where is the authentication logic?"
- "Find all files that use the User model"
- "Show me how the API handles errors"

**CODE**: User wants to write new code or modify existing code
Examples:
- "Add a new endpoint for user registration"
- "Fix the bug in the login function"
- "Refactor the database connection code"

**EXECUTE**: User wants to run a command, test, or build
Examples:
- "Run the tests"
- "Build the Docker image"
- "Check if the server is running"

**QUESTION**: User has a general question about coding, architecture, etc.
Examples:
- "What's the difference between async and sync?"
- "How should I structure this API?"
- "Explain how JWT authentication works"

**MULTI**: The request involves multiple of the above
Examples:
- "Find the login code and fix the timeout issue"
- "Run tests and show me which ones failed"

**ULTRAPLAN**: The user wants deep investigation and a detailed plan before implementation
Examples:
- "ultraplan this codebase"
- "Spend time analyzing the architecture and create a comprehensive refactoring plan"
- "I need a detailed plan before we touch any code"

Respond ONLY in JSON format with no extra text:
{{
    "primary": "SEARCH|CODE|EXECUTE|QUESTION|MULTI|ULTRAPLAN",
    "confidence": 0.0,
    "sub_intents": [],
    "reasoning": "Brief explanation",
    "suggested_agent": "searcher|coder|executor|general|ultraplan"
}}

User message: {user_message}
"""

_INTENT_TO_ROLE: dict[str, AgentRole] = {
    "searcher": AgentRole.SEARCHER,
    "coder": AgentRole.CODER,
    "executor": AgentRole.EXECUTOR,
    "general": AgentRole.GENERAL,
    "ultraplan": AgentRole.ULTRAPLAN,
}

_PRIMARY_TO_ROLE: dict[str, AgentRole] = {
    "SEARCH": AgentRole.SEARCHER,
    "CODE": AgentRole.CODER,
    "EXECUTE": AgentRole.EXECUTOR,
    "QUESTION": AgentRole.GENERAL,
    "MULTI": AgentRole.GENERAL,
    "ULTRAPLAN": AgentRole.ULTRAPLAN,
}

_ULTRAPLAN_KEYWORD_RE = r"\bultraplan\b"


def has_ultraplan_keyword(text: str) -> bool:
    """テキストに 'ultraplan' キーワードが含まれているかを返す。

    Args:
        text: 検査するテキスト

    Returns:
        'ultraplan' キーワードが含まれている場合 True
    """
    import re
    return bool(re.search(_ULTRAPLAN_KEYWORD_RE, text, re.IGNORECASE))


class Intent(Enum):
    """ユーザーの意図。"""

    SEARCH = "search"
    CODE = "code"
    EXECUTE = "execute"
    QUESTION = "question"
    MULTI = "multi"
    ULTRAPLAN = "ultraplan"


@dataclass
class IntentResult:
    """意図分類結果。"""

    primary: Intent
    confidence: float
    sub_intents: list[Intent] = field(default_factory=list)
    reasoning: str = ""
    suggested_agent: AgentRole = AgentRole.GENERAL


class IntentClassifier:
    """LLMを使ってユーザー入力の意図を分類する。"""

    def __init__(self, provider: LLMProvider) -> None:
        """初期化。

        Args:
            provider: LLMプロバイダー
        """
        self.provider = provider

    def classify(
        self,
        user_message: str,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> IntentResult:
        """ユーザーメッセージの意図を分類する。

        'ultraplan' キーワードを含む場合は即座に ULTRAPLAN に分類する。
        LLMにJSON形式で分類させ、構造化されたレスポンスを返す。
        分類失敗時はGENERALにフォールバックする。

        Args:
            user_message: ユーザーメッセージ
            conversation_history: 会話履歴（オプション）

        Returns:
            意図分類結果
        """
        if not user_message.strip():
            return IntentResult(
                primary=Intent.QUESTION,
                confidence=1.0,
                reasoning="Empty message defaults to QUESTION",
                suggested_agent=AgentRole.GENERAL,
            )

        if has_ultraplan_keyword(user_message):
            return IntentResult(
                primary=Intent.ULTRAPLAN,
                confidence=1.0,
                reasoning="'ultraplan' keyword detected — routing to UltraPlanAgent",
                suggested_agent=AgentRole.ULTRAPLAN,
            )

        messages: list[dict[str, Any]] = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": _INTENT_PROMPT.format(user_message=user_message)})

        try:
            response = self.provider.chat(messages=messages, temperature=None)
            return self._parse_response(response.content)
        except Exception:
            return self._fallback_result(user_message)

    def _parse_response(self, content: str) -> IntentResult:
        """LLMレスポンスをIntentResultに変換する。

        Args:
            content: LLMのレスポンステキスト

        Returns:
            意図分類結果
        """
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON found in response")
            data: dict[str, Any] = json.loads(content[start:end])

            primary_str = data.get("primary", "QUESTION").upper()
            primary = Intent[primary_str] if primary_str in Intent.__members__ else Intent.QUESTION

            sub_intents = []
            for s in data.get("sub_intents", []):
                s_upper = s.upper()
                if s_upper in Intent.__members__:
                    sub_intents.append(Intent[s_upper])

            suggested_str = data.get("suggested_agent", "general").lower()
            suggested_agent = _INTENT_TO_ROLE.get(suggested_str, _PRIMARY_TO_ROLE.get(primary_str, AgentRole.GENERAL))

            confidence = float(data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))

            return IntentResult(
                primary=primary,
                confidence=confidence,
                sub_intents=sub_intents,
                reasoning=data.get("reasoning", ""),
                suggested_agent=suggested_agent,
            )
        except Exception:
            return IntentResult(
                primary=Intent.QUESTION,
                confidence=0.3,
                reasoning="Failed to parse classification response",
                suggested_agent=AgentRole.GENERAL,
            )

    def _fallback_result(self, user_message: str) -> IntentResult:
        """フォールバック: キーワードベースで簡易分類する。

        Args:
            user_message: ユーザーメッセージ

        Returns:
            意図分類結果
        """
        lower = user_message.lower()

        if any(kw in lower for kw in ["find", "search", "where", "show me", "look", "grep", "探", "検索", "どこ"]):
            return IntentResult(
                primary=Intent.SEARCH,
                confidence=0.5,
                reasoning="Keyword-based fallback: search keywords detected",
                suggested_agent=AgentRole.SEARCHER,
            )
        if any(kw in lower for kw in ["run", "execute", "test", "build", "実行", "テスト", "ビルド"]):
            return IntentResult(
                primary=Intent.EXECUTE,
                confidence=0.5,
                reasoning="Keyword-based fallback: execute keywords detected",
                suggested_agent=AgentRole.EXECUTOR,
            )
        if any(kw in lower for kw in ["write", "create", "fix", "add", "refactor", "書", "作", "修正", "追加"]):
            return IntentResult(
                primary=Intent.CODE,
                confidence=0.5,
                reasoning="Keyword-based fallback: code keywords detected",
                suggested_agent=AgentRole.CODER,
            )

        return IntentResult(
            primary=Intent.QUESTION,
            confidence=0.4,
            reasoning="Keyword-based fallback: defaulting to QUESTION",
            suggested_agent=AgentRole.GENERAL,
        )
