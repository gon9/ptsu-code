"""CoordinatorモードのメインクラスとSub-agentディスパッチロジック。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ptsu_code.agent.intent import Intent, IntentClassifier, IntentResult
from ptsu_code.agent.sub_agents.base import AgentRole, SubAgent

if TYPE_CHECKING:
    from ptsu_code.agent.runtime import AgentRuntime


@dataclass
class DispatchResult:
    """Sub-agentへのディスパッチ結果。"""

    agent_role: AgentRole
    agent_name: str
    result: str
    intent: IntentResult


class Coordinator:
    """Sub-agentへタスクを振り分ける司令塔。

    1. IntentClassifierでユーザー入力の意図を分類する
    2. 適切なSub-agentを選択する
    3. Sub-agentにディスパッチして結果を返す
    4. MULTI intentの場合は複数のSub-agentを順次実行する
    """

    def __init__(
        self,
        runtime: AgentRuntime,
        classifier: IntentClassifier,
        agents: dict[AgentRole, SubAgent],
    ) -> None:
        """初期化。

        Args:
            runtime: AgentRuntimeインスタンス
            classifier: Intent分類器
            agents: AgentRoleとSub-agentのマッピング
        """
        self.runtime = runtime
        self.classifier = classifier
        self.agents = agents

    def process(
        self,
        user_message: str,
        context: dict[str, Any] | None = None,
        on_dispatch: Any = None,
    ) -> str:
        """ユーザーメッセージを処理する。

        1. Intentを分類する
        2. 適切なSub-agentを選択する
        3. Sub-agentにディスパッチして結果を返す

        Args:
            user_message: ユーザーメッセージ
            context: コンテキスト情報（オプション）
            on_dispatch: ディスパッチ時のコールバック fn(role, name)

        Returns:
            処理結果
        """
        intent = self.classifier.classify(user_message)

        if intent.primary == Intent.MULTI:
            return self._handle_multi(user_message, intent, context, on_dispatch)

        agent = self._select_agent(intent.suggested_agent)
        if on_dispatch:
            on_dispatch(agent.config.role, agent.config.name)

        return agent.run(self.runtime, user_message, context)

    def _select_agent(self, role: AgentRole) -> SubAgent:
        """AgentRoleに対応するSub-agentを返す。

        対応するagentが存在しない場合はGENERALにフォールバックする。

        Args:
            role: AgentRole

        Returns:
            Sub-agentインスタンス
        """
        if role in self.agents:
            return self.agents[role]
        if AgentRole.GENERAL in self.agents:
            return self.agents[AgentRole.GENERAL]
        return next(iter(self.agents.values()))

    def _handle_multi(
        self,
        message: str,
        intent: IntentResult,
        context: dict[str, Any] | None,
        on_dispatch: Any,
    ) -> str:
        """複数意図のリクエストを処理する。

        sub_intentsの順にSub-agentを実行し、結果を統合する。
        重複するロールは1回だけ実行する。

        Args:
            message: ユーザーメッセージ
            intent: 意図分類結果
            context: コンテキスト情報
            on_dispatch: ディスパッチ時のコールバック

        Returns:
            統合された結果
        """
        _intent_to_role = {
            Intent.SEARCH: AgentRole.SEARCHER,
            Intent.CODE: AgentRole.CODER,
            Intent.EXECUTE: AgentRole.EXECUTOR,
            Intent.QUESTION: AgentRole.GENERAL,
        }

        roles_to_run: list[AgentRole] = []
        seen: set[AgentRole] = set()

        for sub_intent in intent.sub_intents:
            role = _intent_to_role.get(sub_intent, AgentRole.GENERAL)
            if role not in seen:
                roles_to_run.append(role)
                seen.add(role)

        if not roles_to_run:
            fallback = self._select_agent(intent.suggested_agent)
            if on_dispatch:
                on_dispatch(fallback.config.role, fallback.config.name)
            return fallback.run(self.runtime, message, context)

        results: list[str] = []
        for role in roles_to_run:
            agent = self._select_agent(role)
            if on_dispatch:
                on_dispatch(agent.config.role, agent.config.name)
            result = agent.run(self.runtime, message, context)
            results.append(f"[{agent.config.name}]\n{result}")

        return "\n\n".join(results)
