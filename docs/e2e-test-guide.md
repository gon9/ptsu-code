---
tags:
  - evaluation
  - testing_guide
aliases:
  - E2Eテスト実施ガイド
---

# E2Eテスト実施ガイド

## 事前準備

### 1. 環境セットアップ

```bash
cd /Users/gon9a/workspace/claude/ptsu-code
uv sync --all-extras
```

### 2. APIキー設定

```bash
# OpenAI
export PTSU_OPENAI_API_KEY=sk-...

# または Anthropic
export PTSU_ANTHROPIC_API_KEY=sk-ant-...
```

### 3. 動作確認

```bash
# バージョン確認
uv run ptsu version

# エコーモードで起動確認
uv run ptsu chat --no-llm
# "exit" で終了
```

---

## テストシナリオ実施手順

### シナリオ1: コードベース理解（Read-only）

**目的**: ファイル読み取りとプロジェクト理解を検証

```bash
uv run ptsu chat --provider openai
```

**テストケース 1-1: プロジェクト構成の説明**
```
You > このプロジェクトの構成を教えて
```

**チェックポイント**:
- [ ] `read_file` ツールが使用された
- [ ] README.md または pyproject.toml を読んだ
- [ ] src/ ディレクトリの構造を説明した
- [ ] 応答が30秒以内に返ってきた
- [ ] 応答が分かりやすい日本語だった

**期待される動作**:
```
Assistant > プロジェクトを調査します...
  ⚡ read_file(path="README.md")
  ⚡ read_file(path="pyproject.toml")
  
このプロジェクトは PTSU という AI エージェント CLI ツールです。
主な構成:
- src/ptsu_code/: メインソースコード
  - cli/: CLI インターフェース
  - agent/: エージェント実行ランタイム
  - agent/tools/: ツール実装
  - agent/providers/: LLM プロバイダー
...
```

**テストケース 1-2: 特定ファイルの機能説明**
```
You > src/ptsu_code/agent/runtime.py の主要な機能は？
```

**チェックポイント**:
- [ ] 正しいファイルパスを特定した
- [ ] `read_file` でファイルを読んだ
- [ ] クラス・メソッドを正確に把握した
- [ ] 主要機能を簡潔に説明した

**テストケース 1-3: ツールの連続使用**
```
You > agent/tools/ 配下のファイルを全て読んで、どんなツールがあるか教えて
```

**チェックポイント**:
- [ ] 複数の `read_file` を実行した
- [ ] 全てのツールファイルを読んだ
- [ ] ツールの一覧と説明を提供した
- [ ] max_turns 内で完了した

---

### シナリオ2: コード修正（Write操作）

**⚠️ 注意**: このテストは実際にファイルを変更します。Git でコミット前の状態を確認してください。

```bash
# 現在の変更を確認
git status

# テスト実行
uv run ptsu chat --provider anthropic
```

**テストケース 2-1: テストケース追加**
```
You > tests/agent/tools/test_base.py に、ToolParameter のバリデーションテストを追加して
```

**チェックポイント**:
- [ ] `read_file` で既存テストを読んだ
- [ ] `read_file` で対象の base.py を読んだ
- [ ] 不足しているテストケースを特定した
- [ ] `write_file` で新しいテストを追加した
- [ ] 変更内容を説明した
- [ ] 既存のテストを壊していない

**検証**:
```bash
# テストが通るか確認
uv run pytest tests/agent/tools/test_base.py -v

# 変更を確認
git diff tests/agent/tools/test_base.py
```

**テストケース 2-2: 設定項目追加**
```
You > src/ptsu_code/config.py に max_retries という設定項目を追加して（デフォルト値は3）
```

**チェックポイント**:
- [ ] `read_file` で config.py を読んだ
- [ ] 適切な位置に設定項目を追加した
- [ ] 型ヒントが正しい
- [ ] デフォルト値が設定されている
- [ ] Docstring が追加されている（あれば）

**検証**:
```bash
# 構文エラーがないか確認
uv run python -c "from ptsu_code.config import settings; print(settings.max_retries)"

# 変更を確認
git diff src/ptsu_code/config.py
```

---

### シナリオ3: コマンド実行とフィードバックループ

```bash
uv run ptsu chat
```

**テストケース 3-1: テスト実行**
```
You > pytest を実行して結果を教えて
```

**チェックポイント**:
- [ ] `execute_command` でテストを実行した
- [ ] 実行結果を正しく解釈した
- [ ] 成功/失敗を報告した
- [ ] カバレッジ情報があれば報告した

**テストケース 3-2: エラー修正ループ**
```
You > ruff check を実行して、エラーがあれば修正して
```

**チェックポイント**:
- [ ] `execute_command` で ruff を実行した
- [ ] エラーがあればファイルを読んだ
- [ ] 修正を適用した
- [ ] 再度 ruff を実行して確認した
- [ ] 無限ループに陥らなかった

**テストケース 3-3: タイムアウト処理**
```
You > sleep 100 を実行して
```

**チェックポイント**:
- [ ] タイムアウト（30秒）が発生した
- [ ] タイムアウトエラーが報告された
- [ ] プロセスが残っていない（`ps aux | grep sleep` で確認）

---

### シナリオ4: プロバイダー切替

**テストケース 4-1: OpenAI**
```bash
uv run ptsu chat --provider openai
```
```
You > src/ptsu_code/agent/runtime.py の AgentSession クラスを説明して
```

**記録**:
- 使用モデル: gpt-4o-mini
- 応答時間: ___ 秒
- ツール使用: [ ] read_file
- 応答品質: ⬜ 優秀 / ⬜ 良好 / ⬜ 要改善

**テストケース 4-2: Anthropic**
```bash
uv run ptsu chat --provider anthropic
```
```
You > src/ptsu_code/agent/runtime.py の AgentSession クラスを説明して
```

**記録**:
- 使用モデル: claude-3-5-sonnet-20241022
- 応答時間: ___ 秒
- ツール使用: [ ] read_file
- 応答品質: ⬜ 優秀 / ⬜ 良好 / ⬜ 要改善

**比較評価**:
- 結果の一貫性: ⬜ 同等 / ⬜ 差異あり
- 速度: OpenAI ⬜ 速い / ⬜ 同等 / ⬜ 遅い
- コメント: 

---

### シナリオ5: エラーハンドリング

```bash
uv run ptsu chat
```

**テストケース 5-1: 存在しないファイル**
```
You > /tmp/nonexistent_file_12345.txt を読んで
```

**チェックポイント**:
- [ ] `read_file` を実行した
- [ ] エラーが返ってきた
- [ ] エラーメッセージが分かりやすい
- [ ] エージェントがパニックしなかった
- [ ] 代替案を提示した（あれば）

**テストケース 5-2: 権限エラー**
```
You > /etc/shadow を読んで
```

**チェックポイント**:
- [ ] 権限エラーが発生した
- [ ] エラーを適切に報告した

**テストケース 5-3: 不正なコマンド**
```
You > invalid_command_xyz を実行して
```

**チェックポイント**:
- [ ] コマンドが見つからないエラーが返った
- [ ] エラーメッセージが分かりやすい

---

## 評価シート

### 機能性

| 項目 | 評価 | コメント |
|------|------|---------|
| ファイル読み取り | ⬜ 優秀 / ⬜ 良好 / ⬜ 要改善 | |
| ファイル書き込み | ⬜ 優秀 / ⬜ 良好 / ⬜ 要改善 | |
| コマンド実行 | ⬜ 優秀 / ⬜ 良好 / ⬜ 要改善 | |
| マルチターン | ⬜ 優秀 / ⬜ 良好 / ⬜ 要改善 | |
| エラーハンドリング | ⬜ 優秀 / ⬜ 良好 / ⬜ 要改善 | |
| プロバイダー互換性 | ⬜ 優秀 / ⬜ 良好 / ⬜ 要改善 | |

### ユーザー体験

| 項目 | 評価 | コメント |
|------|------|---------|
| 応答の分かりやすさ | ⬜ 優秀 / ⬜ 良好 / ⬜ 要改善 | |
| 応答速度 | ⬜ 優秀 / ⬜ 良好 / ⬜ 要改善 | |
| エラーメッセージ | ⬜ 優秀 / ⬜ 良好 / ⬜ 要改善 | |
| CLI の見やすさ | ⬜ 優秀 / ⬜ 良好 / ⬜ 要改善 | |

### 発見された問題

| # | 問題 | 重要度 | 再現手順 |
|---|------|--------|---------|
| 1 | | ⬜ 高 / ⬜ 中 / ⬜ 低 | |
| 2 | | ⬜ 高 / ⬜ 中 / ⬜ 低 | |
| 3 | | ⬜ 高 / ⬜ 中 / ⬜ 低 | |

### Day 3-4 で優先実装すべき機能

評価結果を踏まえ、優先度を決定:

**必須** (評価で「要改善」が多かった項目):
- [ ] 

**推奨** (UX向上のため):
- [ ] 

**検討** (あると便利):
- [ ] 

---

## テスト後のクリーンアップ

```bash
# 変更を確認
git status
git diff

# テストで追加されたファイルを削除（必要に応じて）
git checkout .

# または、良い変更はコミット
git add -p
git commit -m "test: Add test cases from E2E evaluation"
```

---

## 次のアクション

1. この評価結果を `docs/e2e-evaluation.md` に記録
2. 発見された問題を Issue として登録
3. Day 3-4 の実装優先度を調整
4. 実装開始
