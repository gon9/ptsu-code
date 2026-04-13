---
date: 2026-04-13
phase: Day 5-7 完了後の振り返り
completed_steps:
  - Step 6: Sub-agent Protocol
  - Step 7: Intent分類器
  - Step 8: Searcher Agent
  - Step 9a: CoderAgent
  - Step 9b: ExecutorAgent
  - Step 10: Coordinator
  - Step 11: CLI統合
---

# Day 5-7 振り返り（Coordinator Mode 基盤 + 実装）

## 実装内容

### Step 6: Sub-agent Protocol（base.py）
- `AgentRole` Enum: SEARCHER / CODER / EXECUTOR / GENERAL
- `SubAgentConfig` dataclass: allowed_tools, max_turns, temperature
- `SubAgent` 抽象基底クラス: `config` property + `run()` abstract method

### Step 7: Intent分類器（intent.py）
- `Intent` Enum: SEARCH / CODE / EXECUTE / QUESTION / MULTI
- `IntentResult` dataclass: confidence, sub_intents, suggested_agent
- `IntentClassifier`: LLM JSON Mode + キーワードベースフォールバック
- JSON埋め込みテキストからの抽出対応

### Step 8: Searcher Agent（sub_agents/searcher.py）
- 読み取り専用ツール（write_file / execute_command 禁止）
- temperature=0.3（正確性重視）、max_turns=5

### Step 9a: CoderAgent（sub_agents/coder.py）
- read_file + write_file + 検索ツール許可
- temperature=0.3、max_turns=10
- write前にread_file必須の指示をプロンプトに明記

### Step 9b: ExecutorAgent（sub_agents/executor.py）
- execute_command + read_file のみ許可
- temperature=0.1（最低温度・決定論的実行）、max_turns=5
- ソースコード変更禁止をプロンプトに明記

### Step 10: Coordinator（coordinator.py）
- `DispatchResult` dataclass
- `Coordinator.process()`: Intent分類→Sub-agent選択→実行
- MULTI intent: sub_intentsを順次実行、重複ロールをスキップ
- `on_dispatch` コールバックでCLIリアルタイム表示

### Step 11: CLI統合（cli/app.py + cli/ui.py）
- `_build_coordinator()` ヘルパー関数
- `--coordinator / --no-coordinator` フラグ追加
- `show_coordinator_dispatch()` UI関数

## ✅ 良かった点

### 1. **設計書先行の実装が機能した**
- `day5-coordinator-design.md` と `day6-7-coordinator-implementation.md` を先に作成
- 実装中に迷いが少なく、ファイル構成・API設計が明確だった
- 設計書がテスト戦略の指針にもなった

### 2. **ruffルールの徹底**
- セッション途中で `ruff --fix → pytest` の順序をルール化
- 以降はエラーゼロで一発通過（1件の自動修正のみ）
- `global_rules.md` への追記で永続化できた

### 3. **疎結合な Sub-agent 設計**
- `SubAgent` 基底クラスにより、CoderAgent / ExecutorAgent の実装が対称的でシンプル
- `on_dispatch` コールバックで CLI と Coordinator を分離
- ToolRegistry の restricted copy パターンで安全なツール制限を実現

### 4. **テストカバレッジが高水準**
- Coordinator: 98%、intent.py: 99%、base.py: 100%
- parametrize テストで正常系・異常系を効率よくカバー
- Mock/Patch を適切に使い、LLM呼び出しなしで高速テスト

### 5. **フォールバック戦略が堅牢**
- IntentClassifier: JSON parse失敗→キーワード分類→QUESTION
- Coordinator._select_agent: ロール未登録→GENERAL→最初のagent
- MULTI intent の空 sub_intents → フォールバックagent

## ❌ 悪かった点・改善点

### 1. **同じバグを2回踏んだ**
- `self.llm` vs `self.provider` の属性名不一致
- ストリーミングでの Anthropic ツール変換漏れ
- **改善案**: 実装後に即 E2E テストを実行するルール化

### 2. **Sub-agentのrun()が重複コード**
- SearcherAgent / CoderAgent / ExecutorAgent の `run()` 実装がほぼ同じ
- restricted_registry 構築ロジックが3ファイルに重複
- **改善案**: `SubAgent` 基底クラスに `run()` のデフォルト実装を追加

### 3. **session_tool_registry への依存が暗黙的**
- `runtime.session_tool_registry` が存在しない場合の処理が `hasattr` で曖昧
- **改善案**: `AgentRuntime` に `session_tool_registry` を正式なプロパティとして追加

### 4. **Coordinator の MULTI intent が単純すぎる**
- 現在は順次実行するだけで、前の結果を次のagentに渡せない
- **改善案**: DispatchResult を連鎖させ、前のagentの出力をcontextに追加

### 5. **CLIの--coordinatorフラグがセッション固定**
- 途中でCoordinator Mode を切替できない
- **改善案**: チャット内コマンド（`/coordinator on/off`）で動的切替

## 📊 メトリクス

| 指標 | Day 4まで | Day 5-7後 |
|------|-----------|-----------|
| テスト数 | 116件 | 227件 (+111件) |
| カバレッジ | 61% | 69% (+8pt) |
| 新規ソースファイル | — | 6ファイル |
| 新規テストファイル | — | 5ファイル |
| コミット数 | — | 5コミット |

### 新規モジュールのカバレッジ
| モジュール | カバレッジ |
|---|---|
| agent/sub_agents/base.py | 100% |
| agent/intent.py | 99% |
| agent/coordinator.py | 98% |
| agent/sub_agents/coder.py | 96% |
| agent/sub_agents/executor.py | 96% |
| agent/sub_agents/searcher.py | 96% |

## 🎓 学んだこと

1. **設計書を先に書くとコード品質が上がる** — API設計が固まった状態で実装するため、大きなやり直しが発生しない
2. **ruffは先にかける** — pytest前に `ruff --fix` を実行するルールで無駄なリトライがなくなる
3. **フォールバック設計は最初から考える** — LLM応答の不確実性を想定したフォールバックチェーンが品質を高める
4. **Sub-agentのrun()は基底クラスに持つべき** — テンプレートメソッドパターンで重複を排除できる

## 🔜 次のステップへの示唆

- **Sub-agent基底クラスのrun()デフォルト実装** — コード重複を解消してから次の機能追加
- **Coordinator の MULTI intent 改善** — 前のagent結果を次のcontextへ連鎖
- **E2Eテストの自動化** — `uv run ptsu chat --coordinator` の動作確認を自動化
- **runtime の session_tool_registry 正式化** — `hasattr` による暗黙依存を排除
