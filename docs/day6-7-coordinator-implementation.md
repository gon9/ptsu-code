# Day 6-7: Coordinator Mode 実装

---
tags:
  - implementation_plan
  - coordinator
phase: Day 6-7
status: in_progress
---

## 概要

Day 5で構築した Sub-agent Protocol と Intent分類器を活用し、Coordinator Mode を完成させる。
CoderAgent / ExecutorAgent を実装し、Coordinator が全 Sub-agent を統括して CLI から使えるようにする。

## 目標

- CoderAgent / ExecutorAgent を実装する
- Coordinator がIntent分類→Sub-agent選択→結果返却を行う
- MULTI intent（複数意図）を順次処理できる
- `--coordinator` フラグで CLI から切替可能

## アーキテクチャ（完成形）

```
User Input
    │
    ▼
┌────────────────────────────────┐
│  Coordinator                    │
│  1. IntentClassifier.classify() │
│  2. _select_agent(intent)       │
│  3. agent.run(runtime, msg)     │
│  4. (MULTI) 順次実行・結合      │
└────────┬───────────────────────┘
         │
   ┌─────┼──────────┐
   ▼     ▼          ▼
Searcher Coder   Executor
(read)  (write)  (exec)
```

## Step 9a: CoderAgent 実装

### 実装ファイル
- `src/ptsu_code/agent/sub_agents/coder.py`

### 仕様

```python
class CoderAgent(SubAgent):
    role: AgentRole.CODER
    allowed_tools: ["read_file", "write_file", "grep_search", "find_files", "list_directory"]
    temperature: 0.3   # 正確性重視
    max_turns: 10
```

### 特徴

- **読み書き両対応**: write_file 使用可（承認フロー付き）
- 修正前に必ず read_file で内容確認
- 変更後に read_file で検証推奨

## Step 9b: ExecutorAgent 実装

### 実装ファイル
- `src/ptsu_code/agent/sub_agents/executor.py`

### 仕様

```python
class ExecutorAgent(SubAgent):
    role: AgentRole.EXECUTOR
    allowed_tools: ["execute_command", "read_file"]
    temperature: 0.1   # 最低温度で決定論的実行
    max_turns: 5
```

### 特徴

- **コマンド実行専用**: execute_command 使用可（承認フロー付き）
- エラー発生時はログを読んで再試行
- 破壊的コマンドには特に注意

## Step 10: Coordinator 実装

### 実装ファイル
- `src/ptsu_code/agent/coordinator.py`

### データ構造

```python
@dataclass
class DispatchResult:
    agent_role: AgentRole
    agent_name: str
    result: str
    intent: IntentResult

class Coordinator:
    def __init__(self, runtime, classifier, agents): ...
    def process(self, user_message, on_dispatch=None) -> str: ...
    def _select_agent(self, intent) -> SubAgent: ...
    def _handle_multi(self, message, intent) -> str: ...
```

### MULTI intent 処理方針

sub_intents の順に Sub-agent を実行し、結果を連結して返す。
重複するロールは1回だけ実行する。

### コールバック (on_dispatch)

```python
def on_dispatch(role: AgentRole, name: str) -> None:
    # CLI でのリアルタイム表示用
    show_coordinator_dispatch(role, name)
```

## Step 11: CLI 統合

### 変更ファイル
- `src/ptsu_code/cli/app.py` — `--coordinator` フラグ追加
- `src/ptsu_code/cli/ui.py` — `show_coordinator_dispatch()` 追加

### CLI イメージ

```
You > このプロジェクトのテストを実行して

╭─ Coordinator ─────────────────────╮
│ Intent: EXECUTE (confidence: 0.92) │
│ Agent:  Executor                   │
╰────────────────────────────────────╯

[Executor] Running tests...
  ⚡ execute_command(command="uv run pytest")
  ✓ All 171 tests passed
```

## テスト戦略

### CoderAgent: `tests/agent/sub_agents/test_coder.py`
- config の allowed_tools に write_file が含まれる
- read_file / grep_search も含まれる
- run() が runtime.run_loop を呼び出す

### ExecutorAgent: `tests/agent/sub_agents/test_executor.py`
- config の allowed_tools に execute_command が含まれる
- write_file が含まれないことを確認
- temperature が 0.1 であることを確認

### Coordinator: `tests/agent/test_coordinator.py`
- SEARCH intent → SearcherAgent にディスパッチ
- CODE intent → CoderAgent にディスパッチ
- EXECUTE intent → ExecutorAgent にディスパッチ
- QUESTION intent → GENERAL (SearcherAgent) にフォールバック
- MULTI intent → 複数 Sub-agent を順次実行
- on_dispatch コールバックが呼ばれる

## 実装順序

1. CoderAgent (15分) + test_coder.py
2. ExecutorAgent (15分) + test_executor.py
3. Coordinator (30分) + test_coordinator.py
4. UI関数 show_coordinator_dispatch() (10分)
5. CLI統合 --coordinator フラグ (15分)
6. ruff --fix → pytest 全件PASS確認

## 成功基準

- [ ] CoderAgent / ExecutorAgent が動作する
- [ ] Coordinator が全 Intent を正しくルーティングする
- [ ] MULTI intent が順次処理できる
- [ ] `--coordinator` フラグで CLI から切替可能
- [ ] 全テスト PASS、カバレッジ 66% 以上維持
- [ ] ruff clean

## 参考資料

- 元の設計書: `docs/2_agentic-loop-and-coordinator.md` (Line 329-474)
- Day 5 実装: `src/ptsu_code/agent/sub_agents/`
- Intent分類器: `src/ptsu_code/agent/intent.py`
