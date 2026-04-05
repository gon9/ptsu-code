---
tags:
  - implementation_plan
  - agent
  - coordinator
aliases:
  - Agentic Loop & Coordinator Mode 実装計画
phase: week1
---

# Agentic Loop 強化 & Coordinator Mode (Week 1: Day 3-7)

## 概要

Day 1-2 で構築した CLI 基盤と、Phase 1 PR で実装済みの基本 Agentic Loop を土台に、
**実用的なエージェント体験**と**Coordinator Mode（マルチエージェント・ルーター）** を実装する。

## 現状の実装済み機能（Phase 1 PR）

| コンポーネント | 状態 | 備考 |
|---------------|------|------|
| LLM Provider 抽象化 | ✅ 完了 | OpenAI / Anthropic 切替可 |
| Tool 基底クラス・Registry | ✅ 完了 | パラメータ検証、OpenAI スキーマ生成 |
| FileRead / FileWrite Tool | ✅ 完了 | ファイルの読み書き |
| CommandExecution Tool | ✅ 完了 | タイムアウト付きコマンド実行 |
| AgentRuntime (run_loop) | ✅ 完了 | マルチターンのツール呼び出しループ |
| CLI 統合 (--llm / --provider) | ✅ 完了 | プロバイダー選択 |

---

## Day 3-4: Agentic Loop の実用化

### ゴール

- ツール実行時の進捗が CLI 上にリアルタイム表示される
- 破壊的操作（ファイル書き込み・コマンド実行）前にユーザー承認を求める
- ストリーミング応答でレスポンスが逐次表示される
- コードベース検索ツールが使える

### Step 1: ストリーミング応答

**目的**: LLM の応答をトークン単位で逐次表示し、体感速度を改善する。

**変更対象**:
- `src/ptsu_code/agent/providers/base.py` - `stream()` メソッド追加
- `src/ptsu_code/agent/providers/openai_provider.py` - OpenAI ストリーミング実装
- `src/ptsu_code/agent/providers/anthropic_provider.py` - Anthropic ストリーミング実装
- `src/ptsu_code/agent/runtime.py` - `run_turn_stream()` 追加
- `src/ptsu_code/cli/ui.py` - `show_streaming_message()` 追加

```python
# providers/base.py に追加
from collections.abc import Iterator

class LLMProvider(ABC):
    @abstractmethod
    def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        ...
    ) -> Iterator[LLMStreamChunk]:
        """ストリーミングでチャット補完を実行する。"""
        pass

@dataclass
class LLMStreamChunk:
    """ストリーミングチャンク。"""
    content_delta: str = ""
    tool_calls_delta: list[dict[str, Any]] | None = None
    is_final: bool = False
    final_response: LLMResponse | None = None
```

### Step 2: Human-in-the-Loop（承認フロー）

**目的**: 破壊的操作の前にユーザーに確認を求め、安全性を確保する。

**変更対象**:
- `src/ptsu_code/agent/tools/base.py` - `requires_approval` プロパティ追加
- `src/ptsu_code/agent/approval.py` - 承認フロー管理（新規）
- `src/ptsu_code/agent/runtime.py` - ツール実行前の承認チェック
- `src/ptsu_code/cli/ui.py` - 承認 UI コンポーネント

```python
# tools/base.py - Tool に追加
class Tool(ABC):
    @property
    def requires_approval(self) -> bool:
        """破壊的操作の場合 True を返す。"""
        return False

# FileWriteTool, CommandExecutionTool は True を返す
# FileReadTool は False のまま
```

```python
# agent/approval.py
from enum import Enum

class ApprovalDecision(Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ALWAYS_APPROVE = "always_approve"  # 以降同ツールを自動承認

class ApprovalManager:
    """ツール実行の承認を管理する。"""
    
    def __init__(self, auto_approve: bool = False):
        self._auto_approved_tools: set[str] = set()
        self._auto_approve_all = auto_approve
    
    def needs_approval(self, tool: Tool) -> bool:
        """承認が必要か判定する。"""
        ...
    
    def request_approval(self, tool_name: str, args: dict) -> ApprovalDecision:
        """CLIを通じてユーザーに承認を求める。"""
        ...
```

**CLI 表示イメージ**:
```
╭─ Tool Approval Required ─────────────────╮
│ Tool: write_file                          │
│ Path: /Users/gon9/project/src/main.py     │
│ Content: (42 lines)                       │
│                                           │
│ [Y]es / [N]o / [A]lways approve this tool │
╰───────────────────────────────────────────╯
```

### Step 3: ツール実行の進捗表示

**目的**: ツール呼び出し中に何が起きているかをユーザーに可視化する。

**変更対象**:
- `src/ptsu_code/cli/ui.py` - `show_tool_execution()`, `show_tool_result()` 追加

```python
def show_tool_execution(tool_name: str, args: dict[str, Any]) -> None:
    """ツール実行中の表示。"""
    # 例: ⚡ Executing: read_file(path="/src/main.py")

def show_tool_result(tool_name: str, result: ToolResult) -> None:
    """ツール実行結果の表示。"""
    # 例: ✓ read_file: 42 lines read
    # 例: ✗ write_file: Permission denied
```

### Step 4: 追加ツール（コードベース検索）

**目的**: エージェントがプロジェクト内のファイルを検索・探索できるようにする。

**新規ファイル**:
- `src/ptsu_code/agent/tools/search_tools.py`

```python
class GrepTool(Tool):
    """ファイル内のテキスト検索ツール。"""
    # parameters: pattern (str, required), path (str, optional), include (str, optional)
    # subprocess で grep -rn を実行

class FindFileTool(Tool):
    """ファイル名でファイルを検索するツール。"""
    # parameters: pattern (str, required), path (str, optional)
    # subprocess で find を実行

class ListDirectoryTool(Tool):
    """ディレクトリの内容を一覧するツール。"""
    # parameters: path (str, required)
    # os.listdir + stat で情報取得
```

### Step 5: システムプロンプトの設計

**目的**: エージェントの振る舞いを安定させるプロンプトを設計する。

**新規ファイル**:
- `src/ptsu_code/agent/prompts.py` - プロンプトテンプレート管理

```python
SYSTEM_PROMPT = """
You are PTSU, an AI coding assistant running in the user's terminal.

## Your Capabilities
You have access to the following tools:
{tool_descriptions}

## Rules
1. Always read files before modifying them.
2. Explain what you're about to do before using tools.
3. Use tools to verify your changes after making them.
4. If a command fails, analyze the error and try a different approach.
5. Be concise in your responses.

## Current Working Directory
{cwd}
"""
```

---

## Day 5: Coordinator Mode の設計 & 基盤

### ゴール

- Coordinator Mode のアーキテクチャを確定する
- Sub-agent の Protocol / 基底クラスを定義する
- Intent 分類の仕組みを実装する

### アーキテクチャ

```
User Input
    │
    ▼
┌─────────────────────────────┐
│  Coordinator (Router)        │  ← ユーザー入力を解釈し、適切な Sub-agent を選択
│  - Intent Classification     │
│  - Sub-agent Dispatch        │
│  - Result Aggregation        │
└─────────┬───────────────────┘
          │ dispatch
    ┌─────┼─────────────┐
    ▼     ▼             ▼
┌───────┐ ┌──────┐ ┌──────────┐
│Search │ │Coder │ │ Executor │  ← 各 Sub-agent は独自の Tool セットとプロンプトを持つ
│Agent  │ │Agent │ │ Agent    │
└───────┘ └──────┘ └──────────┘
```

### Step 6: Sub-agent Protocol 定義

**新規ファイル**:
- `src/ptsu_code/agent/sub_agents/__init__.py`
- `src/ptsu_code/agent/sub_agents/base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

class AgentRole(Enum):
    """Sub-agent の役割。"""
    SEARCHER = "searcher"      # コードベース調査・検索
    CODER = "coder"            # コード生成・編集
    EXECUTOR = "executor"      # コマンド実行・テスト
    GENERAL = "general"        # 汎用的な質問応答

@dataclass
class SubAgentConfig:
    """Sub-agent の設定。"""
    role: AgentRole
    system_prompt: str
    tools: list[str]           # 使用可能なツール名のリスト
    max_turns: int = 10
    temperature: float = 0.7

class SubAgent(ABC):
    """Sub-agent の基底クラス。"""
    
    @property
    @abstractmethod
    def config(self) -> SubAgentConfig:
        """Sub-agent の設定を返す。"""
        pass
    
    @abstractmethod
    def run(self, runtime: AgentRuntime, message: str) -> str:
        """メッセージを処理して結果を返す。"""
        pass
```

### Step 7: Intent 分類器

**新規ファイル**:
- `src/ptsu_code/agent/intent.py`

```python
from dataclasses import dataclass
from enum import Enum

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

class IntentClassifier:
    """LLM を使ってユーザー入力の意図を分類する。"""
    
    def __init__(self, llm: LLMProvider):
        self.llm = llm
    
    def classify(self, user_message: str, context: list[dict] | None = None) -> IntentResult:
        """ユーザーメッセージの意図を分類する。
        
        LLM に JSON モード で分類させ、構造化されたレスポンスを返す。
        """
        ...
```

**分類プロンプト例**:
```
Classify the user's intent into one of the following categories:
- SEARCH: Wants to find, explore, or understand existing code
- CODE: Wants to write new code or modify existing code
- EXECUTE: Wants to run a command, test, or build
- QUESTION: Has a general question about coding, architecture, etc.
- MULTI: The request involves multiple of the above

Respond in JSON format:
{"primary": "...", "confidence": 0.0-1.0, "sub_intents": [...], "reasoning": "..."}
```

---

## Day 6-7: Coordinator Mode 実装

### ゴール

- Coordinator が入力を受け取り、適切な Sub-agent にディスパッチできる
- Searcher / Coder / Executor の3つの Sub-agent が動作する
- Coordinator Mode の ON/OFF が CLI から切替可能
- 結果が統合されて CLI に表示される

### Step 8: 具体的な Sub-agent 実装

**新規ファイル**:
- `src/ptsu_code/agent/sub_agents/searcher.py`
- `src/ptsu_code/agent/sub_agents/coder.py`
- `src/ptsu_code/agent/sub_agents/executor.py`

#### Searcher Agent
```python
class SearcherAgent(SubAgent):
    """コードベースの調査・検索を担当する Sub-agent。"""
    
    # 使用ツール: read_file, grep, find_file, list_directory
    # プロンプト: 「コードベースを調査し、関連する箇所を特定して報告する」
    # 特徴: 読み取り専用。ファイル書き込みやコマンド実行はしない
```

#### Coder Agent
```python
class CoderAgent(SubAgent):
    """コード生成・編集を担当する Sub-agent。"""
    
    # 使用ツール: read_file, write_file, grep
    # プロンプト: 「既存コードを理解し、修正・新規作成を行う」
    # 特徴: ファイル書き込みが可能。承認フロー付き
```

#### Executor Agent
```python
class ExecutorAgent(SubAgent):
    """コマンド実行・テストを担当する Sub-agent。"""
    
    # 使用ツール: execute_command, read_file
    # プロンプト: 「コマンドを実行し、結果を分析して報告する」
    # 特徴: コマンド実行が可能。承認フロー付き
```

### Step 9: Coordinator 実装

**新規ファイル**:
- `src/ptsu_code/agent/coordinator.py`

```python
class Coordinator:
    """Sub-agent へタスクを振り分ける司令塔。"""
    
    def __init__(
        self,
        runtime: AgentRuntime,
        classifier: IntentClassifier,
        agents: dict[AgentRole, SubAgent],
    ):
        self.runtime = runtime
        self.classifier = classifier
        self.agents = agents
    
    def process(self, user_message: str) -> str:
        """ユーザーメッセージを処理する。
        
        1. Intent を分類
        2. 適切な Sub-agent を選択
        3. Sub-agent にディスパッチ
        4. 結果を整形して返却
        """
        intent = self.classifier.classify(user_message)
        
        if intent.primary == Intent.MULTI:
            return self._handle_multi(user_message, intent)
        
        agent = self._select_agent(intent.primary)
        return agent.run(self.runtime, user_message)
    
    def _select_agent(self, intent: Intent) -> SubAgent:
        """Intent に基づいて Sub-agent を選択する。"""
        mapping = {
            Intent.SEARCH: AgentRole.SEARCHER,
            Intent.CODE: AgentRole.CODER,
            Intent.EXECUTE: AgentRole.EXECUTOR,
            Intent.QUESTION: AgentRole.GENERAL,
        }
        role = mapping.get(intent, AgentRole.GENERAL)
        return self.agents[role]
    
    def _handle_multi(self, message: str, intent: IntentResult) -> str:
        """複数意図のリクエストを処理する。
        
        各 Sub-agent を順番に呼び出し、結果を統合する。
        """
        ...
```

### Step 10: CLI 統合

**変更対象**:
- `src/ptsu_code/cli/app.py` - `--coordinator` フラグ追加

```python
@app.command()
def chat(
    ...
    coordinator: Annotated[bool, typer.Option("--coordinator/--no-coordinator",
        help="Enable Coordinator Mode")] = False,
) -> None:
    """対話モードを起動する。"""
    
    if coordinator and use_llm:
        # Coordinator Mode: Sub-agent 経由で処理
        coordinator_instance = build_coordinator(runtime)
        response = coordinator_instance.process(user_input)
    elif use_llm:
        # Direct Mode: 従来の単一エージェント
        response = runtime.run_loop(session, user_input)
```

**CLI 表示イメージ**:
```
You > このプロジェクトのテストカバレッジを上げて

╭─ Coordinator ─────────────────────────────╮
│ Intent: MULTI (search → code → execute)   │
│ Dispatching to: Searcher → Coder → Exec   │
╰───────────────────────────────────────────╯

[Searcher] Analyzing test coverage...
  ⚡ execute_command(command="uv run pytest --cov-report=term-missing")
  ⚡ read_file(path="src/ptsu_code/agent/runtime.py")
  → Coverage gaps found in runtime.py (41%), app.py (56%)

[Coder] Writing tests for uncovered paths...
  ⚡ read_file(path="tests/agent/test_runtime.py")
  ⚡ write_file(path="tests/agent/test_runtime.py", content="...")
  → Added 5 new test cases

[Executor] Running tests...
  ⚡ execute_command(command="uv run pytest")
  → All 82 tests passed. Coverage: 85%
```

---

## ディレクトリ構成（Day 7 完了時）

```
ptsu-code/
├── src/
│   └── ptsu_code/
│       ├── __init__.py
│       ├── __main__.py
│       ├── config.py
│       ├── exceptions.py
│       ├── cli/
│       │   ├── app.py              # --coordinator フラグ追加
│       │   ├── prompt.py
│       │   └── ui.py               # ツール進捗・承認 UI 追加
│       └── agent/
│           ├── __init__.py
│           ├── runtime.py           # ストリーミング対応
│           ├── approval.py          # 承認フロー管理 [NEW]
│           ├── coordinator.py       # Coordinator 本体 [NEW]
│           ├── intent.py            # Intent 分類器 [NEW]
│           ├── prompts.py           # プロンプトテンプレート [NEW]
│           ├── providers/
│           │   ├── base.py          # stream() メソッド追加
│           │   ├── openai_provider.py
│           │   └── anthropic_provider.py
│           ├── tools/
│           │   ├── base.py          # requires_approval 追加
│           │   ├── registry.py
│           │   ├── file_tools.py
│           │   ├── command_tool.py
│           │   └── search_tools.py  # Grep/Find/ListDir [NEW]
│           └── sub_agents/          # [NEW]
│               ├── __init__.py
│               ├── base.py          # SubAgent Protocol
│               ├── searcher.py
│               ├── coder.py
│               └── executor.py
├── tests/
│   └── agent/
│       ├── test_approval.py         [NEW]
│       ├── test_coordinator.py      [NEW]
│       ├── test_intent.py           [NEW]
│       ├── test_prompts.py          [NEW]
│       ├── sub_agents/              [NEW]
│       │   ├── test_searcher.py
│       │   ├── test_coder.py
│       │   └── test_executor.py
│       └── tools/
│           ├── test_search_tools.py [NEW]
│           └── ...（既存）
└── docs/
    └── 2_agentic-loop-and-coordinator.md  # 本ドキュメント
```

---

## テスト計画

### Day 3-4 のテスト

| テスト対象 | テスト内容 | 優先度 |
|-----------|-----------|--------|
| `search_tools.py` | Grep/Find/ListDir の正常系・異常系 | 高 |
| `approval.py` | 承認フロー（approve/reject/always） | 高 |
| `prompts.py` | テンプレート変数の展開、ツール説明の生成 | 中 |
| ストリーミング | ストリームチャンクの逐次処理 | 中 |
| `ui.py` (追加分) | ツール進捗・承認 UI の表示 | 低 |

### Day 5-7 のテスト

| テスト対象 | テスト内容 | 優先度 |
|-----------|-----------|--------|
| `intent.py` | 各 Intent の分類精度、JSON パース | 高 |
| `sub_agents/base.py` | SubAgent の Protocol 準拠 | 高 |
| `sub_agents/*.py` | 各 Sub-agent のツールセット・プロンプト | 高 |
| `coordinator.py` | Intent → Sub-agent のディスパッチ | 高 |
| `coordinator.py` | MULTI Intent の複数 Sub-agent 呼び出し | 中 |
| CLI 統合 | `--coordinator` フラグの動作 | 中 |

### カバレッジ目標
- 新規モジュール: 80% 以上
- 全体: 75% 以上を維持

---

## 実装順序と依存関係

```
Day 3 ─┬─ Step 1: ストリーミング応答
       ├─ Step 4: 検索ツール（Grep/Find/ListDir）
       └─ Step 5: プロンプト設計

Day 4 ─┬─ Step 2: 承認フロー（Human-in-the-Loop）
       └─ Step 3: ツール進捗表示

Day 5 ─┬─ Step 6: Sub-agent Protocol
       └─ Step 7: Intent 分類器

Day 6 ─── Step 8: Sub-agent 実装 (Searcher/Coder/Executor)

Day 7 ─┬─ Step 9: Coordinator 実装
       └─ Step 10: CLI 統合 + テスト
```

**依存関係**:
- Step 2 (承認) → Step 8 (Sub-agent) で承認付きツール実行
- Step 4 (検索ツール) → Step 8 (Searcher Agent) で検索ツール使用
- Step 6 (Sub-agent Protocol) → Step 8 (具体実装)
- Step 7 (Intent 分類) → Step 9 (Coordinator) で分類結果を使用

---

## 設計上の判断ポイント

### 1. Intent 分類を LLM でやるか、ルールベースでやるか

**結論: LLM ベース（JSON モード）**
- 理由: 自然言語の曖昧さをルールベースで捌くのは限界がある
- トレードオフ: 1リクエストあたりの API コールが +1 増える
- 軽減策: シンプルなコマンド（`/search`, `/code`, `/exec`）での直接指定もサポート

### 2. Sub-agent がセッションを共有するか

**結論: 共有しない（独立セッション）**
- 理由: Sub-agent 間の干渉を防ぎ、各 agent の振る舞いを予測可能にする
- Coordinator が必要な情報（Searcher の調査結果等）を次の Sub-agent のコンテキストに注入する

### 3. Coordinator のフォールバック

**結論: Intent 分類に失敗した場合は General Agent にフォールバック**
- General Agent = 従来の単一エージェント（全ツール使用可能）
- ユーザーにフォールバックしたことを通知する

---

## 完了条件

### Day 3-4 完了条件
- [ ] ストリーミング応答が動作する（トークン逐次表示）
- [ ] `write_file` / `execute_command` 実行前にユーザー承認が求められる
- [ ] ツール実行中に進捗が表示される（ツール名、引数、結果）
- [ ] `grep`, `find_file`, `list_directory` ツールが使える
- [ ] システムプロンプトにツール説明と CWD が含まれる
- [ ] 新規モジュールのカバレッジ 80% 以上

### Day 5 完了条件
- [ ] `SubAgent` 基底クラスが定義されている
- [ ] `IntentClassifier` がユーザー入力を5カテゴリに分類できる
- [ ] Intent 分類のテストが通る

### Day 6-7 完了条件
- [ ] `uv run ptsu chat --coordinator` で Coordinator Mode が起動する
- [ ] Searcher / Coder / Executor の3つの Sub-agent が動作する
- [ ] `MULTI` Intent で複数 Sub-agent が順次呼び出される
- [ ] 各 Sub-agent が適切なツールセットのみを使用する
- [ ] フォールバック（分類失敗時）が動作する
- [ ] Coordinator の UI 表示（Intent, Dispatch 先）が出る
- [ ] ruff チェックが通る
- [ ] pytest が全テストパスする
- [ ] 全体カバレッジ 75% 以上

---

## Day 8 への接続

Day 7 完了後、Week 2 では以下に取り組む:
- **ULTRAPLAN**: Coordinator で検出した複雑なタスクを非同期バックグラウンドで長時間思考
- **KAIROS**: ファイル監視デーモンが変更を検知し、Coordinator 経由で自律提案
- Coordinator Mode の実運用フィードバックを反映したプロンプト改善
