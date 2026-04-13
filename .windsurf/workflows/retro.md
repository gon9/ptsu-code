---
description: 直近の実装フェーズの振り返りドキュメントを作成する
---

## 振り返りワークフロー

1. 直近のgitログから実装内容を確認する
```
git log --oneline -10
```

2. テスト結果とカバレッジを確認する
```
uv run pytest --tb=no -q
```

3. 以下のフォーマットで振り返りドキュメントを `docs/{day番号}-retrospective.md` に作成する

### 振り返りドキュメントのフォーマット

```markdown
---
date: YYYY-MM-DD
phase: Day X 完了後の振り返り
completed_steps:
  - step名1
  - step名2
---

# Day X 振り返り（概要）

## 実装内容

### Step N: 名前
- 実装したこと

## ✅ 良かった点

### 1. **カテゴリ名**
- 詳細

## ❌ 悪かった点・改善点

### 1. **カテゴリ名**
- 問題点
- 改善案

## 📊 メトリクス
- テスト数: X件 (+Y件)
- カバレッジ: X% (→ Y%)
- 新規ファイル数: X
- コミット数: X

## 🎓 学んだこと
1. 教訓1
2. 教訓2

## 🔜 次のステップへの示唆
- 示唆1
- 示唆2
```

4. ドキュメント作成後、git add & commit する
```
git add docs/{day番号}-retrospective.md
git commit -m "docs: Add Day X retrospective"
```
