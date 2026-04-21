# PTSU ULTRAPLAN UAT テスト仕様書

**対象バージョン**: Day 8-10 完了後 (ULTRAPLAN 実装)  
**作成日**: 2026-04-22  
**前提**: Anthropic API キーが `.env` に設定済みであること  

---

## 前提条件

```bash
# API キー確認
cat .env | grep ANTHROPIC

# 起動コマンド（全テスト共通）
uv run ptsu chat --coordinator --provider anthropic --no-stream
```

---

## UAT-UP-01: キーワードトリガー — ULTRAPLAN インテント分類

**目的**: `ultraplan` キーワードで LLM を呼ばずに即 ULTRAPLAN へルーティングされることを確認する。

**入力**:
```
ultraplan the src/ptsu_code/agent directory and give me a one-line plan
```

**期待結果**:
1. `🧠 ULTRAPLAN — Deep investigation mode activated` が表示される
2. LLM が `list_directory` / `read_file` / `grep_search` などのツールを呼ぶ
3. `write_plan` ツールを呼んでプランをファイルへ保存する
4. `exit_plan_mode` ツールを呼ぶ
5. マゼンタのパネルでプラン承認ダイアログが表示される

**合否判定**:
- [ ] `🧠 ULTRAPLAN` メッセージが表示された
- [ ] ツール実行ログが 1 件以上出た
- [ ] `exit_plan_mode` が呼ばれた
- [ ] 承認ダイアログが表示された

---

## UAT-UP-02: プラン承認 — 承認フロー

**目的**: ユーザーが `y` で承認するとプラン内容が返却されてセッションが終了することを確認する。

**前提**: UAT-UP-01 の続き（承認ダイアログが表示されている状態）

**操作**:
```
Approve this plan? → y
```

**期待結果**:
1. `✔ Plan approved. Starting implementation...` が表示される
2. マゼンタパネルに表示されたプラン内容が assistant の最終応答として返る
3. 通常の `You > ` プロンプトに戻る

**合否判定**:
- [ ] `Plan approved` メッセージが表示された
- [ ] プラン内容（Markdown）が返却された
- [ ] 次の入力プロンプトが正常に表示された

---

## UAT-UP-03: プラン却下 — 再計画フロー

**目的**: ユーザーが `n` で却下するとフィードバック付きで LLM がプランを改善し続けることを確認する。

**前提**: UAT-UP-01 の続き（承認ダイアログが表示されている状態）

**操作**:
```
Approve this plan? → n
```

**期待結果**:
1. `➩ Plan rejected. Continuing to refine...` が表示される
2. LLM がツール呼び出しを再開し、計画を改善する
3. 再度 `exit_plan_mode` が呼ばれて承認ダイアログが再表示される

**合否判定**:
- [ ] `Plan rejected` メッセージが表示された
- [ ] LLM が追加のツール呼び出しを行った（ログが増えた）
- [ ] 承認ダイアログが再び表示された

---

## UAT-UP-04: write_plan + exit_plan_mode の連携

**目的**: `write_plan` で `/tmp/ptsu-plan.md` が実際に作成され、`exit_plan_mode` の承認ダイアログにその内容が表示されることを確認する。

**確認方法**: UAT-UP-01〜02 実施後に以下を実行

```bash
cat /tmp/ptsu-plan.md
```

**期待結果**:
- ファイルが存在する
- Markdown 形式でプランが記載されている
- 承認ダイアログに表示されたプランと一致している

**合否判定**:
- [ ] `/tmp/ptsu-plan.md` が存在する
- [ ] ファイルに Markdown コンテンツがある
- [ ] ダイアログの内容と一致している

---

## UAT-UP-05: 大文字キーワード — ULTRAPLAN (大文字)

**目的**: 大文字でも ULTRAPLAN ルーティングが機能することを確認する。

**入力**:
```
ULTRAPLAN this project and summarize the architecture
```

**期待結果**: UAT-UP-01 と同様に `🧠 ULTRAPLAN` が表示される

**合否判定**:
- [ ] `🧠 ULTRAPLAN` が表示された

---

## UAT-UP-06: 非 ULTRAPLAN キーワード — 通常ルーティング

**目的**: `ultraplan` を含まないメッセージは通常の Coordinator ルーティングに回されることを確認する。

**入力**:
```
list the files in src/
```

**期待結果**:
- `🧠 ULTRAPLAN` は表示されない
- Searcher/General エージェントにルーティングされる

**合否判定**:
- [ ] `ULTRAPLAN` が表示されなかった
- [ ] 通常エージェントがルーティングされた

---

## エビデンス記録テンプレート

実施後は以下を `docs/uat-ultraplan-evidence-YYYYMMDD.md` に記録する。

```markdown
# ULTRAPLAN UAT 実行エビデンス

**実行日時**: YYYY-MM-DD  
**実行者**: （名前）  
**環境**: macOS M4, Python 3.12, Anthropic claude-3-5-sonnet

| テスト ID | タイトル | 判定 | 備考 |
|---|---|---|---|
| UAT-UP-01 | キーワードトリガー | ✅ PASS / ❌ FAIL | |
| UAT-UP-02 | 承認フロー | ✅ PASS / ❌ FAIL | |
| UAT-UP-03 | 却下・再計画フロー | ✅ PASS / ❌ FAIL | |
| UAT-UP-04 | write_plan ファイル確認 | ✅ PASS / ❌ FAIL | |
| UAT-UP-05 | 大文字キーワード | ✅ PASS / ❌ FAIL | |
| UAT-UP-06 | 非 ULTRAPLAN 通常ルーティング | ✅ PASS / ❌ FAIL | |
```
