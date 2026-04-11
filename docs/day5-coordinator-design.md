# Day 5: Coordinator Mode 設計書

## 概要

Day 5では、複数のSub-agentを統括するCoordinator Modeの基盤を構築します。
ユーザーの入力意図を分類し、適切なSub-agentにタスクを振り分ける仕組みを実装します。

## 目標

- Coordinator Modeのアーキテクチャを確定する
- Sub-agentのProtocol/基底クラスを定義する
- Intent分類の仕組みを実装する
- 基本的なSub-agent（Searcher）を実装する

## アーキテクチャ

```
User Input
    │
    ▼
┌─────────────────────────────┐
│  Coordinator (Router)        │  ← ユーザー入力を解釈し、適切なSub-agentを選択
│  - Intent Classification     │
│  - Sub-agent Dispatch        │
│  - Result Aggregation        │
└─────────┬───────────────────┘
          │ dispatch
    ┌─────┼─────────────┐
    ▼     ▼             ▼
┌───────┐ ┌──────┐ ┌──────────┐
│Search │ │Coder │ │ Executor │  ← 各Sub-agentは独自のToolセットとプロンプトを持つ
│Agent  │ │Agent │ │ Agent    │
└───────┘ └──────┘ └──────────┘
```

## Step 6: Sub-agent Protocol 定義

### 目的
Sub-agentの共通インターフェースを定義し、Coordinatorが統一的に扱えるようにする。

### 実装ファイル
- `src/ptsu_code/agent/sub_agents/__init__.py`
- `src/ptsu_code/agent/sub_agents/base.py`

### データ構造

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

class AgentRole(Enum):
    """Sub-agentの役割。"""
    SEARCHER = "searcher"      # コードベース調査・検索
    CODER = "coder"            # コード生成・編集
    EXECUTOR = "executor"      # コマンド実行・テスト
    GENERAL = "general"        # 汎用的な質問応答

@dataclass
class SubAgentConfig:
    """Sub-agentの設定。"""
    role: AgentRole
    name: str
    description: str
    system_prompt: str
    allowed_tools: list[str]   # 使用可能なツール名のリスト
    max_turns: int = 10
    temperature: float = 0.7

class SubAgent(ABC):
    """Sub-agentの基底クラス。"""
    
    @property
    @abstractmethod
    def config(self) -> SubAgentConfig:
        """Sub-agentの設定を返す。"""
        pass
    
    @abstractmethod
    def run(
        self,
        runtime: AgentRuntime,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """メッセージを処理して結果を返す。
        
        Args:
            runtime: AgentRuntime インスタンス
            message: ユーザーメッセージ
            context: コンテキスト情報（オプション）
            
        Returns:
            処理結果
        """
        pass
```

### 設計のポイント

1. **役割の明確化**: 各Sub-agentは特定の役割に特化
2. **ツール制限**: allowed_toolsで使用可能なツールを制限し、安全性を確保
3. **独立性**: 各Sub-agentは独立して動作可能
4. **拡張性**: 新しいSub-agentを追加しやすい設計

## Step 7: Intent 分類器

### 目的
ユーザーの入力から意図を自動判定し、適切なSub-agentを選択する。

### 実装ファイル
- `src/ptsu_code/agent/intent.py`

### データ構造

```python
from dataclasses import dataclass
from enum import Enum
from typing import Any

class Intent(Enum):
    """ユーザーの意図。"""
    SEARCH = "search"          # コードを調べてほしい
    CODE = "code"              # コードを書いてほしい・修正してほしい
    EXECUTE = "execute"        # コマンドを実行してほしい
    QUESTION = "question"      # 質問に答えてほしい
    MULTI = "multi"            # 複数の意図が含まれる

@dataclass
class IntentResult:
    """意図分類結果。"""
    primary: Intent
    confidence: float          # 0.0 ~ 1.0
    sub_intents: list[Intent]  # 複数意図の場合の詳細
    reasoning: str             # 分類理由
    suggested_agent: AgentRole # 推奨Sub-agent

class IntentClassifier:
    """LLMを使ってユーザー入力の意図を分類する。"""
    
    def __init__(self, provider: LLMProvider):
        self.provider = provider
    
    def classify(
        self,
        user_message: str,
        conversation_history: list[dict] | None = None,
    ) -> IntentResult:
        """ユーザーメッセージの意図を分類する。
        
        Args:
            user_message: ユーザーメッセージ
            conversation_history: 会話履歴（オプション）
            
        Returns:
            意図分類結果
        """
        pass
```

### 分類プロンプト

```python
INTENT_CLASSIFICATION_PROMPT = """Classify the user's intent into one of the following categories:

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

Respond in JSON format:
{
    "primary": "SEARCH|CODE|EXECUTE|QUESTION|MULTI",
    "confidence": 0.0-1.0,
    "sub_intents": ["SEARCH", "CODE"],
    "reasoning": "Brief explanation of why this classification was chosen",
    "suggested_agent": "searcher|coder|executor|general"
}

User message: {user_message}
"""
```

### 実装のポイント

1. **JSON Mode使用**: 構造化された出力を確実に取得
2. **信頼度スコア**: 低信頼度の場合はユーザーに確認
3. **会話履歴考慮**: 前の会話を考慮してより正確に分類
4. **フォールバック**: 分類失敗時はGENERAL agentにフォールバック

## Step 8: Searcher Agent 実装

### 目的
コードベースの調査・検索に特化したSub-agentを実装する。

### 実装ファイル
- `src/ptsu_code/agent/sub_agents/searcher.py`

### 仕様

```python
class SearcherAgent(SubAgent):
    """コードベースの調査・検索を担当するSub-agent。"""
    
    @property
    def config(self) -> SubAgentConfig:
        return SubAgentConfig(
            role=AgentRole.SEARCHER,
            name="Searcher",
            description="Explores and searches the codebase",
            system_prompt=self._get_system_prompt(),
            allowed_tools=[
                "read_file",
                "grep_search",
                "find_files",
                "list_directory",
            ],
            max_turns=5,
            temperature=0.3,  # 低めの温度で正確性重視
        )
    
    def _get_system_prompt(self) -> str:
        return """You are a Searcher Agent specialized in exploring codebases.

Your role:
- Find relevant files and code sections
- Understand code structure and dependencies
- Provide clear summaries of findings
- DO NOT modify any files
- DO NOT execute any commands

Available tools:
- read_file: Read file contents
- grep_search: Search for patterns in files
- find_files: Find files by name
- list_directory: List directory contents

Best practices:
1. Start with broad searches (grep, find)
2. Read relevant files to understand context
3. Provide structured summaries
4. Include file paths and line numbers in your findings
"""
```

### 特徴

- **読み取り専用**: ファイル書き込みやコマンド実行は不可
- **低温度**: 正確性を重視（temperature=0.3）
- **少ターン**: 検索は通常1-3ターンで完了（max_turns=5）
- **構造化出力**: ファイルパスと行番号を含む明確な報告

## テスト戦略

### Step 6: Sub-agent Protocol テスト
- `tests/agent/sub_agents/test_base.py`
  - AgentRoleのEnum値テスト
  - SubAgentConfigのバリデーション
  - SubAgent基底クラスの抽象メソッドテスト

### Step 7: Intent分類器テスト
- `tests/agent/test_intent.py`
  - 各Intentタイプの分類精度テスト
  - 信頼度スコアの妥当性テスト
  - エッジケース（空文字列、長文など）
  - Mock LLMを使った単体テスト

### Step 8: Searcher Agent テスト
- `tests/agent/sub_agents/test_searcher.py`
  - 設定の正確性テスト
  - ツール制限のテスト
  - 検索タスクの実行テスト（Mock使用）
  - システムプロンプトの内容テスト

## 実装順序

1. **Sub-agent Protocol** (30分)
   - base.py: AgentRole, SubAgentConfig, SubAgent
   - テスト: test_base.py

2. **Intent分類器** (45分)
   - intent.py: Intent, IntentResult, IntentClassifier
   - テスト: test_intent.py

3. **Searcher Agent** (30分)
   - searcher.py: SearcherAgent
   - テスト: test_searcher.py

4. **統合テスト** (15分)
   - 各コンポーネントの連携確認

## 成功基準

- [ ] Sub-agent基底クラスが定義され、拡張可能
- [ ] Intent分類器が80%以上の精度で意図を判定
- [ ] SearcherAgentが検索タスクを正常に実行
- [ ] 全テストがPASS
- [ ] カバレッジ80%以上維持
- [ ] ruffチェックがPASS

## 次のステップ（Day 6-7）

- CoderAgent実装
- ExecutorAgent実装
- Coordinator実装
- CLI統合（--coordinator フラグ）
- マルチエージェント連携テスト

## 参考資料

- Day 3-4振り返り: `docs/day3-retrospective.md`
- 元の設計書: `docs/2_agentic-loop-and-coordinator.md`
- テストベストプラクティス: メモリに保存済み
