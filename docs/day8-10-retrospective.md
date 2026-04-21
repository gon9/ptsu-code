---
date: 2026-04-22
phase: Day 8-10 完了後の振り返り
completed_steps:
  - plan_tools.py (WritePlanTool + ExitPlanModeTool)
  - Anthropic Extended Thinking 対応
  - UltraPlanAgent 実装
  - IntentClassifier ULTRAPLAN キーワード検知
  - Coordinator ULTRAPLAN ルーティング
  - CLI / UI ULTRAPLAN 統合
  - テスト追加 (+31件)
---

# Day 8-10 振り返り（ULTRAPLAN 実装）

## 実装内容

### Step 1: plan_tools.py — WritePlanTool + ExitPlanModeTool
- `WritePlanTool`: LLM がプラン内容を Markdown ファイルへ書き込むツール。承認不要。
- `ExitPlanModeTool`: 承認が必要なステートフルなツール。`execute()` 呼び出し時に `plan_approved=True` をセットする。`reset()` メソッドで状態をクリアできる。

### Step 2: Anthropic Extended Thinking 対応
- `AnthropicProvider.chat()` / `stream()` に `thinking_budget: int | None` 引数を追加。
- `thinking_budget` 指定時は `thinking={"type": "enabled", "budget_tokens": N}` を API に渡す。
- Thinking 有効時は temperature を設定しない（API 制約）。`max_tokens` は `max(16000, budget * 2)` に自動スケール。
- `thinking` ブロックは `chat()` のパース時にスキップ（text ブロックのみ返却）。

### Step 3: UltraPlanAgent
- `AgentRole.ULTRAPLAN` を enum に追加。
- `UltraPlanAgent.run()` は `runtime.run_loop()` を使わずカスタムループを実装。
- `exit_plan_mode_tool.plan_approved` フラグを各ターン後にチェックし、承認されたらループ脱出。
- Anthropic プロバイダー使用時に `thinking_budget=10_000` を自動付与。

### Step 4: IntentClassifier ULTRAPLAN キーワード検知
- `has_ultraplan_keyword(text)` 関数を追加（`\bultraplan\b` 正規表現）。
- `classify()` の冒頭でキーワード検知 → LLM 呼び出しをバイパスして即 ULTRAPLAN を返す。
- `Intent.ULTRAPLAN` / `_PRIMARY_TO_ROLE["ULTRAPLAN"]` / `_INTENT_TO_ROLE["ultraplan"]` を追加。

### Step 5: Coordinator ULTRAPLAN ルーティング
- `coordinator.process()` に `Intent.ULTRAPLAN` 分岐を追加。
- `_handle_ultraplan()` メソッドで `UltraPlanAgent` へディスパッチ。

### Step 6: CLI / UI 統合
- `app.py`: `UltraPlanAgent` を `_build_coordinator()` に登録。`WritePlanTool` / `ExitPlanModeTool` をセッションのツールレジストリに登録。
- `ui.py`: `show_ultraplan_progress()` (ターン/経過時間表示)、`show_plan_approval_request()` (Markdown プランを Panel に表示)、`show_coordinator_dispatch()` に ULTRAPLAN スタイル追加。
- `show_tool_approval_request()` が `exit_plan_mode` を検知して専用ダイアログへ振り分け。

## ✅ 良かった点

### 1. **ステートフルツールによるクリーンな承認フロー**
- `ExitPlanModeTool` が `plan_approved` フラグを保持し、`UltraPlanAgent` が it を参照してループ制御する設計はシンプルで追いやすい。
- 既存の `requires_approval` / `execute_tool_calls` の承認フローをそのまま活用できた。

### 2. **キーワードバイパスによるレイテンシ削減**
- `ultraplan` キーワード検知は LLM 呼び出し前に判定されるため、分類コストがゼロ。
- 大文字小文字を問わず検知できる実装が簡潔。

### 3. **Extended Thinking の後方互換設計**
- `thinking_budget=None` がデフォルトのため、既存の `AnthropicProvider` 利用コードへの影響なし。
- temperature が無効化される API 制約を条件分岐（`elif`）で自然に表現できた。

### 4. **テスト戦略：`patch.object(_get_runtime)` で実 API 呼び出しを完全排除**
- `UltraPlanAgent` は config で Anthropic を指定するため、OpenAI runtime から呼ぶと `_get_runtime` が実 Anthropic インスタンスを生成する問題が発覚。
- `patch.object(agent, "_get_runtime", return_value=mock_runtime)` で解決。

## ❌ 悪かった点・改善点

### 1. **path 内キーワードの偽陽性（未対応）**
- `src/ultraplan/foo.ts` のようなファイルパスに含まれる "ultraplan" も検知してしまう。
- claude-code-main では括弧・引用符・パスコンテキストを除外する高度なロジックがある。
- 現在は簡易実装のため、テストで当該ケースを除外してドキュメントに記録するにとどめた。

### 2. **`stream` メソッドでの thinking ブロックハンドリング未実装**
- `chat()` では `thinking` ブロックをスキップしているが、`stream()` は未対応（ストリームイベントに `thinking_delta` が混在する可能性）。
- `UltraPlanAgent` は現在 `chat()` のみ使うため実害はないが、将来的に修正が必要。

### 3. **`run_loop` の再利用機会を逃した**
- カスタムループを `run()` に実装したが、`runtime.run_loop()` のツール実行ロジック（自動承認・ターン制限）と一部重複している。
- `run_loop` にフック機能（ターン後コールバック等）を追加することで、カスタムループの必要性を排除できた可能性がある。

### 4. **テストでの `_get_runtime` パッチが定型コード化**
- 4 つのテストメソッドそれぞれで同じ `patch.object` パターンを繰り返している。
- `@pytest.fixture` または `setUp` ヘルパーに共通化すればテストがスリムになった。

## 📊 メトリクス
- テスト数: 359 件 (+31 件)
- カバレッジ: 86% (前回 87% → 86%、新ファイル追加による微減)
- `plan_tools.py` カバレッジ: 100%
- 新規ファイル: 3 (`plan_tools.py`, `ultraplan.py`, `day8-10-retrospective.md`)
- 変更ファイル: 6 (`anthropic_provider.py`, `base.py`, `intent.py`, `coordinator.py`, `app.py`, `ui.py`)
- コミット数: 0 (本振り返り後にコミット予定)

## 🎓 学んだこと
1. **ステートフルなツールは「フラグ経由の制御フロー」を可能にする** — `requires_approval` が False でも、ツールオブジェクト自体に状態を持たせることでエージェントループの終了条件を外部から制御できる。
2. **`_get_runtime` がプロバイダーを再選択するアーキテクチャはテスト時に落とし穴になる** — Sub-agent が独自プロバイダーを指定する場合、テストで `_get_runtime` をパッチしないと実 API が呼ばれる。
3. **Anthropic Extended Thinking は `temperature` と共存できない** — `thinking` 有効時に `temperature` を渡すと API エラーになる。`elif` 条件で自然に排他制御できる。

## 🔜 次のステップへの示唆
- `stream()` での thinking ブロックスキップ対応（`content_block_start` の `type == "thinking"` を無視）
- `has_ultraplan_keyword` のパスコンテキスト除外（ファイルパス内の "ultraplan" を無視）
- `run_loop` へのフック機能追加（ターン後コールバック）による `UltraPlanAgent` のカスタムループ削減
- ULTRAPLAN 承認後の実装フェーズ連携（承認済みプランを Coder/Executor に渡す仕組み）
