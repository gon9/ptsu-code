# Day 18-21 Design — Session Memory (Dream System MVP)

## Open Items 解決

| # | 項目 | 決定 |
|---|---|---|
| 1 | 命名 | `memory` パッケージ / 機能名 "Session Memory" |
| 2 | 発動タイミング | CLI レベルで各ターン後に同期実行（MVP は非同期化しない） |
| 3 | Token counter | `len(content) // 4` (rough estimation, Claude Code 準拠) |
| 4 | Session ID | `datetime.now().strftime("%Y%m%d_%H%M%S")` |
| 5 | 失敗時挙動 | warning ログ + スキップ（セッション進行に影響させない） |
| 6 | 注入ポリシー | 起動時に `~/.ptsu/session-memory/current.md` を自動読込み注入。空なら注入しない |

## アーキテクチャ

```
src/ptsu_code/memory/
  __init__.py      - SessionMemoryManager のみ公開
  models.py        - SessionMemoryConfig, SessionMemoryState
  template.py      - DEFAULT_TEMPLATE (Claude Code の 10 セクション)
  storage.py       - SessionMemoryStorage (atomic write, archive)
  triggers.py      - estimate_tokens(), should_extract()
  extractor.py     - MemoryExtractor (LLM 呼び出し + バリデーション)
  manager.py       - SessionMemoryManager (上記を統合)
```

## ストレージ設計

- 現在のメモリ: `~/.ptsu/session-memory/current.md`
- アーカイブ: `~/.ptsu/session-memory/archive/<session_id>.md`（セッション終了時）
- アトミック書き込み: `.current.tmp` → `replace()` で更新

## 発動条件

```
Initialization 閾値: total_tokens >= 8_000
Update 閾値 (initialized 後):
  tokens_since_last >= 4_000
  AND tool_calls_since_last >= 3
```

（Claude Code より小さめ：ptsu-code のセッションは短い傾向があるため）

## Extractor プロンプト設計

System prompt:
- 「セッションノート更新エージェント」として振る舞う
- テンプレート構造（# ヘッダー, _italic descriptions_）を必ず保持
- italic descriptions より下にのみ内容を書く
- 出力はマークダウン全文のみ

User message:
```
Conversation:
<会話履歴テキスト>

Current session notes:
<current_memory>

Output the updated session notes:
```

## CLI 統合フロー

```
起動時:
  memory_dir = ~/.ptsu/session-memory
  manager = SessionMemoryManager(provider, session_id, memory_dir)
  prev_memory = manager.load_previous()
  if prev_memory:
      session.add_message("system", f"## Previous Session Memory\n{prev_memory}")

各ターン後:
  manager.add_turn(user_input, response, tool_call_count)
  manager.maybe_extract()  # 条件満たせば抽出 (非同期化なし MVP)

終了時:
  manager.finalize()  # アーカイブへ保存
```

## /summary ツール

`SummaryTool`:
- description: "Manually extract and save session memory"
- 引数なし
- `manager.force_extract()` を呼び出し
- 結果のメモリパスを返す
