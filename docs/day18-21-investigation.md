---
tags:
  - investigation
  - dream-system
  - memory
  - compaction
  - day18-21
phase: Day 18-21 — Dream System 調査
sources:
  - claude-code-main/src/services/SessionMemory/
  - claude-code-main/src/services/compact/
  - claude-code-main/src/commands/memory/memory.tsx
status: 調査完了（仕様書・実装は次セッション）
---

# Day 18-21 — Dream System 調査ノート

## 概要

`imple-plan.md` の「Dream System = 対話ログを解析してユーザーの癖・よく間違えるコマンドを抽出し、次回以降の system prompt に反映するバッチ処理」に対応する実機能を claude-code-main で調査した結果、**SessionMemory** が直系の類似機能として存在することを確認。あわせて関連する **compact**（コンテキスト圧縮）と **/memory**（永続記憶）についても調べた。

本書は実装前の **調査専用メモ**。仕様書と実装は別セッションで行う。

---

## 1. SessionMemory（核心機能）

### 1-1. 役割

- セッション中の会話から「重要情報」を **markdown ファイル** に自動抽出し、常に最新化する
- バックグラウンドで動く（メインループをブロックしない）
- 次回セッション起動時や `/compact` 時にコンテキストへ自動注入される

### 1-2. ファイル構成

`claude-code-main/src/services/SessionMemory/`
| ファイル | 役割 |
|---|---|
| `sessionMemory.ts` (496 行) | post-sampling hook 登録、抽出トリガ、forked agent 起動 |
| `sessionMemoryUtils.ts` (208 行) | 設定 / 状態管理（閾値、最終抽出トークン数など） |
| `prompts.ts` (325 行) | テンプレート定義、抽出プロンプト生成、セクションサイズ監視 |

### 1-3. テンプレート（核心）

Claude Code の **固定 10 セクション** (DEFAULT_SESSION_MEMORY_TEMPLATE):

```md
# Session Title
_A short and distinctive 5-10 word descriptive title_

# Current State
_What is actively being worked on right now?_

# Task specification
_What did the user ask to build?_

# Files and Functions
_What are the important files?_

# Workflow
_What bash commands are usually run?_

# Errors & Corrections        ← ★ptsu の「よく間違えるコマンド」に該当
_Errors encountered and how they were fixed._

# Codebase and System Documentation
_What are the important system components?_

# Learnings                    ← ★ptsu の「コーディングの癖」に該当
_What has worked well? What to avoid?_

# Key results
_Exact output the user requested_

# Worklog
_Step by step, what was attempted_
```

italic `_descriptions_` は **編集禁止のテンプレート指示**。LLM はこの下にのみ内容を書く。

### 1-4. 抽出の発動条件

`shouldExtractMemory(messages)` — **AND 条件**:

1. **Initialization 閾値**: `minimumMessageTokensToInit = 10,000 tokens` を初めて超えた時に "initialized" フラグを立てる
2. **Update 閾値** (initialized 後):
   - Token growth `minimumTokensBetweenUpdate = 5,000 tokens` 以上
   - **AND** Tool calls `toolCallsBetweenUpdates = 3 回` 以上
   - **OR** 最後のターンで tool calls なし（= 自然な区切り） + token 閾値達成

```ts
const shouldExtract =
  (hasMetTokenThreshold && hasMetToolCallThreshold) ||
  (hasMetTokenThreshold && !hasToolCallsInLastTurn)
```

→ **要点**: Token 閾値は必須。Tool call だけ進んでも token 足りなければ抽出しない（無駄な LLM コールを抑制）。

### 1-5. 抽出フロー

```
post-sampling hook firing
   ↓
shouldExtractMemory()?
   ↓ yes
setupSessionMemoryFile()      # ~/.claude/session-memory/<id>.md を作成（初回はテンプレで埋める）
   ↓
buildSessionMemoryUpdatePrompt(currentMemory, memoryPath)
   ↓
runForkedAgent({              # 別 agent context で非同期実行
  promptMessages,
  canUseTool: Edit のみ、かつ memoryPath 限定,
  querySource: 'session_memory',
  forkLabel: 'session_memory',
})
   ↓
recordExtractionTokenCount()  # 次回閾値計算のため
updateLastSummarizedMessageIdIfSafe()
```

### 1-6. 権限制約

`createMemoryFileCanUseTool(memoryPath)`:
- `FileEditTool` のみ許可
- `file_path` が memoryPath に完全一致するときのみ allow
- それ以外は deny

→ **Why**: forked agent が暴走してコードベースを変更しないよう厳しく絞る。

### 1-7. サイズ管理

- **per-section**: `MAX_SECTION_LENGTH = 2,000 tokens`
- **total**: `MAX_TOTAL_SESSION_MEMORY_TOKENS = 12,000 tokens`
- 超過時は `generateSectionReminders()` がプロンプトに警告を追加、LLM が自発的に圧縮
- `truncateSessionMemoryForCompact()` は compact 時の注入用に物理切り詰めも行う（section 境界で切断）

### 1-8. カスタマイズ（外部ファイル）

- `~/.claude/session-memory/config/template.md` — 独自テンプレート上書き
- `~/.claude/session-memory/config/prompt.md` — 独自抽出プロンプト上書き (`{{currentNotes}}`, `{{notesPath}}` 変数)

### 1-9. 手動トリガ

`manuallyExtractSessionMemory()` を `/summary` コマンドから呼び出し。閾値バイパス。

---

## 2. Compact（コンテキスト圧縮）

### 2-1. 階層構造

| 種類 | トリガ | 戦略 |
|---|---|---|
| **autoCompact** | context window が `threshold = effective - 13k buffer` 到達 | 自動 |
| **sessionMemoryCompact** | autoCompact 内で優先試行 | SessionMemory 要約で置換 |
| **legacy compact** | sessionMemoryCompact 失敗時 | LLM で全履歴サマリ生成 |
| **microCompact** | 常時 | 古い tool results（FileRead/Grep/Bash 等）のみクリア |
| **reactive compact** | API 413 error 時 | 緊急圧縮 |
| **manual /compact** | ユーザー実行 | 即座に圧縮 |

### 2-2. 閾値定義（`autoCompact.ts`）

```ts
AUTOCOMPACT_BUFFER_TOKENS      = 13_000   // auto 発動まで残るバッファ
WARNING_THRESHOLD_BUFFER_TOKENS = 20_000  // UI 警告
ERROR_THRESHOLD_BUFFER_TOKENS   = 20_000  // エラー色
MANUAL_COMPACT_BUFFER_TOKENS    =  3_000  // 手動 compact 用最低バッファ
MAX_OUTPUT_TOKENS_FOR_SUMMARY   = 20_000  // summary 用出力確保

effectiveContextWindow = modelContextWindow - MAX_OUTPUT_TOKENS_FOR_SUMMARY
autoCompactThreshold   = effectiveContextWindow - AUTOCOMPACT_BUFFER_TOKENS
```

環境変数で override 可:
- `CLAUDE_CODE_AUTO_COMPACT_WINDOW` — context window 手動指定
- `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` — 割合指定（0-100）
- `DISABLE_COMPACT` / `DISABLE_AUTO_COMPACT`

### 2-3. Circuit breaker

- `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3`
- 3 回連続失敗でそのセッションは以降 auto compact を試みない
- Why: 過去 1,279 セッションで 50+ 回の失敗を検知、合計 250K API call/day を浪費していた

### 2-4. sessionMemoryCompact の戦略 (`sessionMemoryCompact.ts`)

```
DEFAULT_SM_COMPACT_CONFIG = {
  minTokens:             10_000,  # 保持する最低 tokens
  minTextBlockMessages:       5,  # 保持する最低メッセージ数
  maxTokens:             40_000,  # 保持する上限 (hard cap)
}
```

流れ:
1. `lastSummarizedMessageId` 以降のメッセージは保持対象
2. 後ろから前へ遡って `minTokens` または `minTextBlockMessages` に達するまで拡張
3. `maxTokens` に達したら打ち切り
4. `adjustIndexToPreserveAPIInvariants()` で **tool_use / tool_result ペアが分割されないよう** 境界を調整（これ重要：分割すると API エラーになる）
5. SessionMemory の中身 + 最新 N メッセージ = post-compact の状態

### 2-5. microCompact の対象ツール

`COMPACTABLE_TOOLS`: FileRead, FileWrite, FileEdit, Grep, Glob, WebFetch, WebSearch, Shell 系

→ これら **ツールの結果** だけが古いメッセージから順に消える。thinking や text は残る。

---

## 3. /memory command（CLAUDE.md 編集）

- 単純な機能: `$EDITOR` または `$VISUAL` で CLAUDE.md や `~/.claude/memory*` ファイルを開く
- Dialog で複数の memory file 候補から選択させる
- Claude Code の **永続的記憶** (project-level CLAUDE.md, user-level ~/.claude/memory.md 等) を編集する純粋な UI コマンド

→ これは Dream System には直接関係ないが、「永続メモリ」を **編集可能なファイル** として露出する UX は参考になる。

---

## 4. ptsu-code への移植マッピング

### 4-1. Dream System = SessionMemory MVP

| Claude Code | ptsu-code 対応案 |
|---|---|
| `~/.claude/session-memory/<id>.md` | `.ptsu/session-memory/<session-id>.md` |
| `DEFAULT_SESSION_MEMORY_TEMPLATE` (10 セクション) | そのまま借用 (日本語化は後回し) |
| post-sampling hook | `AgentRuntime.run_loop` 完了後のフック or 明示的 `after_turn` イベント |
| `runForkedAgent` (別 agent context 非同期) | **MVP は同期実行でよい**。発動時はユーザーに待ちが発生する前提 |
| `canUseTool` で Edit のみ | ptsu は FileWriteTool + path 検証でよい (schedule_tools と同じパターン) |
| `/summary` コマンド | `/summary` スラッシュコマンドまたは `dream_extract` ツール |
| Initialization: 10,000 tokens | ptsu の実使用に合わせて再調整（8k 前後？） |
| Update: 5,000 tokens + 3 tool calls | そのまま |
| per-section 2k / total 12k | そのまま |
| 外部 template/prompt カスタマイズ | **MVP ではスキップ** |

### 4-2. Compaction は別タスク

- ptsu-code はまだ長大セッションが発生しないので、**Compaction は Day 18-21 の範囲外**とし将来タスクに回す
- 必要になったら sessionMemoryCompact の戦略 (直近 N メッセージ + memory summary) をそのまま採用できる
- microCompact（tool results の段階的クリア）は手軽で効果大、短期的にでも有効
- ただし **tool_use / tool_result ペア保全** (`adjustIndexToPreserveAPIInvariants`) は移植時の落とし穴になり得るので要注意

### 4-3. 次セッション起動時の注入

Claude Code の流れ:
1. セッション再開時 `getSessionMemoryContent()` でファイル読み込み
2. compact 時やセッション開始時に system prompt または最初の user message に埋め込む

ptsu-code の流れ（案）:
1. 起動時 `AgentSession` 初期化前に `SessionMemory.load_latest()` を呼ぶ
2. 内容があれば `system` role メッセージとして追加:
   ```
   ## Previous Session Summary
   <memory.md 内容>
   ```
3. または coding_assistant() system prompt にセクションとして join

---

## 5. アーキテクチャ設計の要点

### 5-1. 抽象化レベル

```
ptsu_code/
  memory/                         ← 新規パッケージ（"dream" より汎用的でよい）
    __init__.py
    models.py                     # SessionMemory dataclass
    storage.py                    # ファイル I/O (atomic write)
    extractor.py                  # LLM を呼んで抽出 (forked 風)
    template.py                   # デフォルトテンプレート
    triggers.py                   # 閾値判定 (tokens, tool_calls)
  agent/
    tools/
      memory_tools.py             # /summary, dream_extract 等のツール
```

### 5-2. 依存

- **tiktoken** or provider別 token counter が必要（token 閾値判定のため）
- 既存 `AgentSession.messages` / `ToolRegistry` はそのまま利用可

### 5-3. テスト容易性

- `shouldExtract()` は pure function（messages + state → bool）→ unit test 容易
- `extractor.extract()` は LLM を呼ぶが、provider を mock 可能
- `storage.save()` は atomic write（Schedule と同パターン）

---

## 6. オープン項目（仕様確定前に決める）

1. **「Dream」という名称を使うか**
   - imple-plan では Dream System だが、実機能は SessionMemory に近い
   - 候補: `memory`, `session_memory`, `dream`, `journal`
   - **推奨**: `memory` パッケージ + 機能名 "Session Memory"（Claude Code 準拠）。"Dream" は将来の Ollama バックグラウンド処理用にとっておく
2. **発動タイミング**
   - `run_loop` 完了後の同期実行 vs 非同期スレッド
   - **推奨**: MVP は同期（UX に軽いレイテンシ）、後で async 化
3. **Token counter**
   - tiktoken を直接使う vs `provider.count_tokens()` 実装を増やす
   - **推奨**: `provider.count_tokens(messages)` を `LLMProvider` 基底に追加
4. **Session 識別子**
   - セッション ID（timestamp or uuid）の生成方法と、複数セッションの扱い
   - **推奨**: 起動時に `YYYYMMDD_HHMMSS` 形式で生成、最新のみ "current.md" として symlink、過去は `archive/<id>.md`
5. **LLM 抽出の失敗時挙動**
   - ファイル更新せずスキップ？ backup？
   - **推奨**: 失敗ログだけ残してスキップ（セッション進行に影響させない）
6. **注入タイミング**
   - 次セッション起動時に注入するが、always? confirm?
   - **推奨**: デフォ auto、`--no-memory` フラグで無効化可能

---

## 7. 次セッションへの申し送り

### 実装前にやること
1. **仕様書作成**: `docs/day18-21-memory-design.md`
   - オープン項目 1-6 を決定
   - ファイル構成・API 決定
   - テンプレートの最終決定（Claude Code の 10 セクション そのままか、ptsu 独自か）
2. **依存追加**: tiktoken（または equivalent） to `pyproject.toml`
3. **Token counter**: `LLMProvider.count_tokens()` を追加（openai / anthropic 各実装）

### 実装手順（TDD で）
- Phase 1: `memory/models.py` + `memory/storage.py` + tests
- Phase 2: `memory/triggers.py` (shouldExtract ロジック) + tests
- Phase 3: `memory/extractor.py` (LLM 呼び出し) + tests (mock)
- Phase 4: `AgentRuntime` 統合 (run_loop 後フック)
- Phase 5: 次セッション注入 (`cli/app.py`)
- Phase 6: `/summary` ツール

### レトロ用メモ
- SessionMemory の 10 セクションテンプレは秀逸（そのまま使う価値大）
- sessionMemoryCompact の `adjustIndexToPreserveAPIInvariants` は tool_use/tool_result ペア保全の良い参考例
- Circuit breaker パターン（autoCompact の 3 連続失敗で停止）は ptsu にも有用

---

## 8. 参考ソースコード位置

| 項目 | パス |
|---|---|
| SessionMemory main | `claude-code-main/src/services/SessionMemory/sessionMemory.ts` |
| 閾値・設定 | `claude-code-main/src/services/SessionMemory/sessionMemoryUtils.ts` |
| テンプレート & プロンプト | `claude-code-main/src/services/SessionMemory/prompts.ts` |
| autoCompact | `claude-code-main/src/services/compact/autoCompact.ts` |
| SM compact | `claude-code-main/src/services/compact/sessionMemoryCompact.ts` |
| microCompact | `claude-code-main/src/services/compact/microCompact.ts` |
| /memory cmd | `claude-code-main/src/commands/memory/memory.tsx` |
