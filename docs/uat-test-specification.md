# PTSU UAT テスト仕様書

**対象バージョン**: Week 1 完了 (Day 1-7)
**作成日**: 2026-04-13
**テスト担当**: ユーザー（UAT）

---

## 前提条件

### 環境要件
- Python 3.12 以上（または Docker）
- uv インストール済み
- OpenAI API キー（LLM モードのテストに必要）

### セットアップ

```bash
# 1. 依存インストール
cd /Users/gon9a/workspace/claude/ptsu-code
uv sync

# 2. 環境変数設定（.envファイル）
cp .env.example .env
# .env に PTSU_OPENAI_API_KEY=<your-key> を設定

# 3. 動作確認
uv run ptsu --help
```

### テスト用ファイル準備

```bash
# テスト用ディレクトリ作成
mkdir -p /tmp/ptsu-uat/src
echo "def hello(): return 'world'" > /tmp/ptsu-uat/src/main.py
echo "import os\nprint(os.getcwd())" > /tmp/ptsu-uat/src/script.py
```

---

## テストケース一覧

| ID | カテゴリ | テスト名 | 優先度 |
|---|---|---|---|
| UAT-01 | CLI基盤 | バージョン表示 | 高 |
| UAT-02 | CLI基盤 | ヘルプ表示 | 高 |
| UAT-03 | CLI基盤 | ウェルカム画面 | 高 |
| UAT-04 | CLI基盤 | エコーモード（LLMなし）| 高 |
| UAT-05 | CLI基盤 | exit コマンド | 高 |
| UAT-06 | CLI基盤 | help コマンド | 中 |
| UAT-07 | LLMモード | LLMモード起動 | 高 |
| UAT-08 | LLMモード | 基本的な質問応答 | 高 |
| UAT-09 | LLMモード | APIキーなし時のフォールバック | 中 |
| UAT-10 | ツール | ファイル読み取り | 高 |
| UAT-11 | ツール | ファイル書き込み（承認あり）| 高 |
| UAT-12 | ツール | コマンド実行（承認あり）| 高 |
| UAT-13 | ツール | grep 検索 | 中 |
| UAT-14 | ツール | ファイル検索 | 中 |
| UAT-15 | ツール | ディレクトリ一覧 | 中 |
| UAT-16 | ストリーミング | ストリーミング応答 | 高 |
| UAT-17 | ストリーミング | ストリーミング無効化 | 低 |
| UAT-18 | Coordinator | Coordinator Mode 起動確認 | 高 |
| UAT-19 | Coordinator | SEARCH インテント | 高 |
| UAT-20 | Coordinator | CODE インテント | 高 |
| UAT-21 | Coordinator | EXECUTE インテント | 高 |
| UAT-22 | Coordinator | MULTI インテント | 中 |

---

## 詳細テストケース

---

### [UAT-01] バージョン表示

**目的**: `ptsu version` コマンドでバージョンが表示される

**手順**:
```bash
uv run ptsu version
```

**期待結果**:
```
PTSU version X.X.X
```

**合否基準**: バージョン番号が表示されること

---

### [UAT-02] ヘルプ表示

**目的**: `--help` フラグでコマンド一覧が表示される

**手順**:
```bash
uv run ptsu --help
uv run ptsu chat --help
```

**期待結果** (`ptsu --help`):
- `chat` サブコマンドが表示される
- `version` サブコマンドが表示される

**期待結果** (`ptsu chat --help`):
- `--llm/--no-llm` オプション
- `--stream/--no-stream` オプション
- `--coordinator/--no-coordinator` オプション
- `--provider` オプション
- `--verbose/-v` オプション

**合否基準**: 全オプションが説明付きで表示されること

---

### [UAT-03] ウェルカム画面

**目的**: 起動時にリッチな装飾付きウェルカム画面が表示される

**手順**:
```bash
uv run ptsu chat --no-llm
# 起動後すぐに exit と入力して終了
```

**期待結果**:
- `PTSU - AI Agent CLI` が枠（パネル）付きで表示される
- バージョン番号が表示される
- `exit/quit/Ctrl+D` の終了方法が表示される
- `help` コマンドの案内が表示される

**合否基準**: パネル装飾付きでウェルカム画面が表示されること

---

### [UAT-04] エコーモード（LLMなし）

**目的**: `--no-llm` モードでメッセージがそのままエコーバックされる

**手順**:
```bash
uv run ptsu chat --no-llm
# プロンプトが表示されたら以下を入力:
> Hello PTSU
> テストメッセージ
> exit
```

**期待結果**:
- `You > Hello PTSU` と入力後、`Assistant: Echo: Hello PTSU` と表示される
- 各メッセージがエコーバックされる
- `exit` で正常終了する

**合否基準**: 入力内容が `Echo: <入力>` 形式でエコーバックされること

---

### [UAT-05] exit コマンドと Ctrl+D

**目的**: 複数の終了方法が機能する

**手順**:
```bash
# テスト 1: exit コマンド
uv run ptsu chat --no-llm
> exit

# テスト 2: quit コマンド
uv run ptsu chat --no-llm
> quit

# テスト 3: Ctrl+D
uv run ptsu chat --no-llm
# Ctrl+D を入力
```

**期待結果**: いずれも `Goodbye!` が表示されて正常終了する（終了コード 0）

**合否基準**: 3通りの終了方法すべてで正常終了すること

---

### [UAT-06] help コマンド

**目的**: チャット内で `help` と入力するとコマンド一覧が表示される

**手順**:
```bash
uv run ptsu chat --no-llm
> help
```

**期待結果**:
- `exit, quit` の説明
- `help` の説明
- Echo mode の説明

**合否基準**: コマンド一覧が表示されること

---

### [UAT-07] LLMモード起動

**目的**: LLMモードで起動し、ツール数とプロバイダーが表示される

**前提**: `.env` に `PTSU_OPENAI_API_KEY` が設定済み

**手順**:
```bash
uv run ptsu chat
# 起動確認後 exit
> exit
```

**期待結果**:
- `LLM mode enabled (openai) with 6 tools available.` と表示される
- 利用可能ツール数が **6** であること

**合否基準**: LLM モードが有効化され、6ツールが登録されること

---

### [UAT-08] 基本的な質問応答

**目的**: LLMにシンプルな質問を送り、応答が返ってくる

**前提**: LLMモード有効、API キー設定済み

**手順**:
```bash
uv run ptsu chat
> Pythonでフィボナッチ数列を計算する関数を書いて
> exit
```

**期待結果**:
- Pythonのコードを含む応答が返ってくる
- ストリーミングでトークンが逐次表示される（デフォルト）
- `Assistant:` プレフィックスが付く

**合否基準**: LLMからコードを含む応答が返ってくること

---

### [UAT-09] APIキーなし時のフォールバック

**目的**: APIキーが未設定の場合、エコーモードにフォールバックする

**手順**:
```bash
# 一時的にAPIキーを外してテスト
PTSU_OPENAI_API_KEY="" uv run ptsu chat
> Hello
```

**期待結果**:
- `OpenAI API key is not configured.` エラーメッセージが表示される
- `Falling back to echo mode.` と表示される
- その後エコーモードで動作する

**合否基準**: エラー後にエコーモードで継続動作すること

---

### [UAT-10] ファイル読み取りツール

**目的**: エージェントが `read_file` ツールを使ってファイルを読む

**前提**: LLMモード有効

**手順**:
```bash
uv run ptsu chat
> /tmp/ptsu-uat/src/main.py というファイルの内容を読んで教えて
```

**期待結果**:
- `⚡ Executing: read_file(...)` が表示される
- `✓ read_file: ...` の結果が表示される
- ファイルの内容（`def hello(): return 'world'`）が応答に含まれる

**合否基準**: ツール実行ログが表示され、ファイル内容を正しく読み取ること

---

### [UAT-11] ファイル書き込み（承認フロー）

**目的**: `write_file` 実行前に承認プロンプトが表示される

**前提**: LLMモード有効

**手順**:
```bash
uv run ptsu chat
> /tmp/ptsu-uat/output.py というファイルに "print('hello')" と書いて
# 承認プロンプトが出たら:
# Y = 承認して実行
# N = 拒否して中断
```

**期待結果**:
- `Tool Approval Required` のようなプロンプトが表示される
- `write_file` とファイルパスが表示される
- `[Y]es / [N]o / [A]lways` の選択肢が表示される
- **Y を入力した場合**: ファイルが作成され、結果が表示される
- **N を入力した場合**: `Tool execution rejected by user` となりファイルは作成されない

**合否基準**: 承認プロンプトが表示され、Y/N で動作が分岐すること

---

### [UAT-12] コマンド実行（承認フロー）

**目的**: `execute_command` 実行前に承認プロンプトが表示される

**前提**: LLMモード有効

**手順**:
```bash
uv run ptsu chat
> pwd コマンドを実行して現在のディレクトリを教えて
# 承認プロンプトが出たら Y を入力
```

**期待結果**:
- 承認プロンプトが表示される
- Y 入力後にコマンドが実行される
- 実行結果（カレントディレクトリ）が応答に含まれる

**合否基準**: 承認後にコマンドが実行され結果が返ること

---

### [UAT-13] grep 検索ツール

**目的**: エージェントが `grep_search` ツールを使ってコードを検索する

**前提**: LLMモード有効

**手順**:
```bash
uv run ptsu chat
> /tmp/ptsu-uat/src ディレクトリで "def" を含む行を検索して
```

**期待結果**:
- `grep_search` ツールが呼ばれる
- `def hello()` の行が見つかる
- 検索結果がファイル名と行番号付きで表示される

**合否基準**: grep 検索が実行され結果が返ること

---

### [UAT-14] ファイル検索ツール

**目的**: エージェントが `find_files` ツールを使ってファイルを探す

**前提**: LLMモード有効

**手順**:
```bash
uv run ptsu chat
> /tmp/ptsu-uat ディレクトリで .py ファイルを探して一覧を出して
```

**期待結果**:
- `find_files` ツールが呼ばれる
- `main.py` と `script.py` が見つかる

**合否基準**: `.py` ファイルが正しく列挙されること

---

### [UAT-15] ディレクトリ一覧ツール

**目的**: エージェントが `list_directory` ツールを使う

**前提**: LLMモード有効

**手順**:
```bash
uv run ptsu chat
> /tmp/ptsu-uat の中にあるファイルとディレクトリを一覧で見せて
```

**期待結果**:
- `list_directory` ツールが呼ばれる
- `src/` ディレクトリが含まれる一覧が表示される

**合否基準**: ディレクトリ内容が表示されること

---

### [UAT-16] ストリーミング応答

**目的**: 応答がトークン単位で逐次表示される（デフォルト動作）

**前提**: LLMモード有効

**手順**:
```bash
uv run ptsu chat  # デフォルト: --stream
> 100文字程度で量子コンピュータについて説明して
```

**期待結果**:
- `Assistant:` が先に表示される
- テキストが少しずつ（逐次）表示される（一気に表示されない）

**合否基準**: レスポンスがストリーミングで表示されること

---

### [UAT-17] ストリーミング無効化

**目的**: `--no-stream` フラグで非ストリーミング動作に切り替わる

**前提**: LLMモード有効

**手順**:
```bash
uv run ptsu chat --no-stream
> Pythonとは何ですか？
```

**期待結果**:
- 応答が一括で表示される
- `Assistant:` プレフィックス付きで応答が表示される

**合否基準**: 応答が返ること（ストリーミングとの視覚的違いを確認）

---

### [UAT-18] Coordinator Mode 起動確認

**目的**: `--coordinator` フラグで Coordinator Mode が有効になる

**前提**: LLMモード有効

**手順**:
```bash
uv run ptsu chat --coordinator
# 起動メッセージを確認して exit
> exit
```

**期待結果**:
- LLM モードが有効化される
- チャットが起動する（エラーなし）

**合否基準**: Coordinator Mode でエラーなく起動すること

---

### [UAT-19] Coordinator — SEARCH インテント

**目的**: コード検索要求が Searcher Agent にディスパッチされる

**前提**: LLMモード有効、API キー設定済み

**手順**:
```bash
uv run ptsu chat --coordinator
> このプロジェクトのどこで AgentRuntime クラスが定義されているか調べて
```

**期待結果**:
- `Dispatching to Searcher` のような UI 表示が出る（Searcher ロールの色付き表示）
- コードベースを検索するツール呼び出しが行われる
- AgentRuntime の定義場所が応答に含まれる

**合否基準**: Searcher Agent へのディスパッチが表示され、検索結果が返ること

---

### [UAT-20] Coordinator — CODE インテント

**目的**: コード作成要求が Coder Agent にディスパッチされる

**前提**: LLMモード有効

**手順**:
```bash
uv run ptsu chat --coordinator
> /tmp/ptsu-uat/utils.py にリスト内の最大値を返す関数を書いて
# write_file の承認プロンプトが出たら Y
```

**期待結果**:
- `Dispatching to Coder` のような UI 表示が出る
- 承認プロンプトの後にファイルが作成される
- 応答でコードの説明がある

**合否基準**: Coder Agent へのディスパッチが表示され、ファイルが作成されること

---

### [UAT-21] Coordinator — EXECUTE インテント

**目的**: コマンド実行要求が Executor Agent にディスパッチされる

**前提**: LLMモード有効

**手順**:
```bash
uv run ptsu chat --coordinator
> uv run pytest tests/ --tb=no -q を実行してテスト結果を教えて
# execute_command の承認プロンプトが出たら Y
```

**期待結果**:
- `Dispatching to Executor` のような UI 表示が出る
- 承認後にテストが実行される
- テスト結果（passed/failed 数）が応答に含まれる

**合否基準**: Executor Agent へのディスパッチが表示され、コマンド実行結果が返ること

---

### [UAT-22] Coordinator — MULTI インテント

**目的**: 複数の意図を含むリクエストで複数の Sub-agent が順次呼ばれる

**前提**: LLMモード有効

**手順**:
```bash
uv run ptsu chat --coordinator
> src/ptsu_code/agent/runtime.py を読んで、その内容をもとに /tmp/ptsu-uat/summary.md にサマリーを書いて
# write_file の承認が出たら Y
```

**期待結果**:
- 複数の Sub-agent が呼ばれる（MULTI インテント）
- Searcher または Coder Agent が呼ばれる表示が出る
- `/tmp/ptsu-uat/summary.md` が作成される

**合否基準**: 複数の操作（読み込み→書き込み）が連続して完了すること

---

## Docker テスト（オプション）

Docker 環境でも同一動作が確認できること。

```bash
# ビルド
docker compose build

# エコーモード起動
docker compose run --rm dev ptsu chat --no-llm

# LLMモード起動（環境変数を渡す）
PTSU_OPENAI_API_KEY=<your-key> docker compose run --rm dev ptsu chat
```

**合否基準**: ローカルと同じ動作が Docker 内でも確認できること

---

## テスト結果記録表

| テスト ID | テスト名 | 結果 (PASS/FAIL) | メモ |
|---|---|---|---|
| UAT-01 | バージョン表示 | | |
| UAT-02 | ヘルプ表示 | | |
| UAT-03 | ウェルカム画面 | | |
| UAT-04 | エコーモード | | |
| UAT-05 | exit/quit/Ctrl+D | | |
| UAT-06 | help コマンド | | |
| UAT-07 | LLM モード起動 | | |
| UAT-08 | 基本質問応答 | | |
| UAT-09 | APIキーなしフォールバック | | |
| UAT-10 | ファイル読み取り | | |
| UAT-11 | ファイル書き込み（承認） | | |
| UAT-12 | コマンド実行（承認） | | |
| UAT-13 | grep 検索 | | |
| UAT-14 | ファイル検索 | | |
| UAT-15 | ディレクトリ一覧 | | |
| UAT-16 | ストリーミング | | |
| UAT-17 | ストリーミング無効 | | |
| UAT-18 | Coordinator 起動 | | |
| UAT-19 | SEARCH インテント | | |
| UAT-20 | CODE インテント | | |
| UAT-21 | EXECUTE インテント | | |
| UAT-22 | MULTI インテント | | |

---

## 既知の制限事項・注意点

1. **Coordinator Mode はストリーミング非対応**: `--coordinator --stream` を指定しても、Coordinator 経由の応答は非ストリーミング（一括表示）
2. **API コスト**: Coordinator Mode は Intent 分類で追加の API コールが発生する（1リクエストあたり +1 コール）
3. **MULTI インテント**: 前の Sub-agent の詳細な出力は次の Sub-agent のコンテキストに渡されない（現バージョンの制限）
4. **Docker**: `PTSU_ANTHROPIC_API_KEY` は `docker-compose.yml` に未設定のため、Anthropic を使う場合は個別指定が必要

---

## UAT 完了基準

- 高優先度テスト（UAT-01〜08, 10〜12, 16, 18〜21）が全て **PASS**
- 中優先度テスト（UAT-06, 09, 13〜15, 17, 22）が 80% 以上 **PASS**
- クリティカルな障害（CLI 起動不能、LLM 応答なし）がゼロ
