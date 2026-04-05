---
tags:
  - implementation_plan
  - cli
  - setup
aliases:
  - CLIフロントエンド基盤構築
phase: week1
---

# CLIフロントエンド基盤構築 (Week 1: Day 1-2)

## 概要

30日間ロードマップの Day 1 として、プロジェクトの基盤構築とリッチなCLIフロントエンドの実装を行う。
Day 2 以降で Agentic Loop や Coordinator Mode を組み込むための土台を作ることが目的。

## ゴール

- `uv run ptsu` コマンドでCLIが起動する
- ウェルカム画面が Rich で装飾表示される
- REPL形式の対話ループ（入力 → エコーバック）が動作する
- Docker Compose で開発環境が再現可能
- ruff / pytest が通る状態

---

## ディレクトリ構成

```
ptsu-code/
├── docs/
│   ├── imple-plan.md          # 30日間ロードマップ
│   └── day1-plan.md           # 本ドキュメント
├── src/
│   └── ptsu_code/
│       ├── __init__.py        # パッケージ初期化、バージョン定義
│       ├── __main__.py        # `python -m ptsu_code` エントリーポイント
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── app.py         # Typerアプリ定義 & メインコマンド
│       │   ├── prompt.py      # prompt_toolkit による対話入力
│       │   └── ui.py          # Rich UIコンポーネント (ウェルカム, パネル等)
│       └── config.py          # pydantic-settings による設定管理
├── tests/
│   ├── __init__.py
│   └── cli/
│       ├── __init__.py
│       └── test_app.py        # CLIの基本テスト
├── Dockerfile                 # マルチステージビルド
├── docker-compose.yml         # 開発環境定義
├── pyproject.toml             # プロジェクト設定 (uv, ruff, pytest)
└── README.md                  # プロジェクト概要
```

---

## 技術選定

| カテゴリ | 技術 | 用途 |
|---------|------|------|
| 言語 | Python 3.12 | メイン開発言語 |
| パッケージ管理 | uv | 依存管理・仮想環境・スクリプト実行 |
| CLIフレームワーク | Typer | コマンド定義・引数解析 |
| ターミナルUI | Rich | 装飾テキスト・パネル・テーブル表示 |
| 対話入力 | prompt_toolkit | 補完・履歴付きのREPL入力 |
| 設定管理 | pydantic-settings | 環境変数ベースの設定バリデーション |
| Linter/Formatter | ruff | コード品質管理 |
| テスト | pytest | ユニットテスト |
| コンテナ | Docker + Docker Compose | 開発環境の統一 |

---

## 実装ステップ

### Step 1: uv によるプロジェクト初期化

- `uv init` でプロジェクト作成
- `pyproject.toml` に依存パッケージ追加:
  - `typer[all]`, `rich`, `prompt-toolkit`, `pydantic-settings`
  - dev: `ruff`, `pytest`, `pytest-cov`
- CLIスクリプトエントリーポイント `ptsu` を定義

### Step 2: プロジェクトディレクトリ構成の作成

- `src/ptsu_code/` パッケージと `tests/` ディレクトリを作成
- 各 `__init__.py` を配置

### Step 3: 基本CLIエントリーポイント実装

**`src/ptsu_code/cli/app.py`**
- Typer アプリの定義
- `chat` サブコマンド: 対話モード起動
- `version` サブコマンド: バージョン表示
- `--verbose` オプション: デバッグ出力の切り替え

**`src/ptsu_code/__main__.py`**
- `python -m ptsu_code` で `cli/app.py` の Typer アプリを呼び出す

### Step 4: CLI UIコンポーネント実装

**`src/ptsu_code/cli/ui.py`**
- `show_welcome()`: ロゴ + バージョン + ヒント表示 (Rich Panel)
- `show_message(role, content)`: ユーザー/アシスタントのメッセージ表示
- `show_error(message)`: エラー表示
- `show_spinner(message)`: 処理中インジケーター

**`src/ptsu_code/cli/prompt.py`**
- `get_user_input()`: prompt_toolkit による入力取得
  - 履歴保存
  - Ctrl+C / Ctrl+D ハンドリング
  - 複数行入力サポート（将来拡張用の設計）

### Step 5: 設定管理

**`src/ptsu_code/config.py`**
- `Settings` クラス (pydantic-settings の BaseSettings)
  - `app_name`: アプリ名 (デフォルト: "ptsu")
  - `version`: バージョン
  - `openai_api_key`: OpenAI API キー (Day 3以降で使用)
  - `verbose`: デバッグモード
  - `history_dir`: 履歴保存ディレクトリ

### Step 6: Docker / Docker Compose

**`Dockerfile`** (マルチステージビルド)
- Stage 1 (builder): uv で依存インストール
- Stage 2 (runtime): 最小イメージで実行

**`docker-compose.yml`**
- `dev` サービス: ソースコードをマウント、対話モードで起動

### Step 7: ruff 設定 + pytest テスト

**ruff設定** (`pyproject.toml` 内)
- line-length: 120
- target-version: "py312"

**テスト** (`tests/cli/test_app.py`)
- 正常系: CLIが起動しバージョン表示できること
- 正常系: `--help` が正しく表示されること
- 異常系: 不正なサブコマンドでエラーになること

---

## 設計方針

### 拡張性を意識した疎結合設計

```
[CLI Layer]          [Agent Layer (Day 3~)]     [Tool Layer (Day 3~)]
cli/app.py    →      agent/loop.py        →     tools/file.py
cli/prompt.py        agent/coordinator.py        tools/command.py
cli/ui.py            agent/planner.py            tools/search.py
```

- CLI層は入出力のみを担当し、ビジネスロジックを持たない
- Day 3 以降で Agent Layer を追加する際、CLI層への変更は最小限にする
- 各層はインターフェース（Protocol / ABC）で疎結合にする

### 対話ループの基本フロー (Day 1 時点)

```
起動 → ウェルカム表示 → [入力待ち → エコーバック表示 → 入力待ち ...] → 終了
```

Day 3 以降で「エコーバック」部分を LLM 呼び出しに置き換える。

---

## 完了条件

- [ ] `uv run ptsu` でCLIが起動する
- [ ] ウェルカム画面が表示される
- [ ] 対話入力 → エコーバック → 再入力のループが動く
- [ ] `exit` / `quit` / Ctrl+D で正常終了する
- [ ] `uv run ptsu version` でバージョンが表示される
- [ ] `docker compose run --rm dev ptsu` で同じ動作ができる
- [ ] `uv run ruff check src/ tests/` がパスする
- [ ] `uv run pytest` が全テストパスする

---

## Day 2 への接続

Day 1 完了後、Day 2 では以下に取り組む:
- CLI UIの洗練（テーマ・カラースキーム調整、ステータスバー追加）
- 設定ファイル（TOML/YAML）読み込みの追加
- `prompt_toolkit` のカスタマイズ（キーバインド、補完）
- 基本的なログ機構の導入
