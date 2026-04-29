"""Session Memory のファイル I/O。

アトミック書き込み・アーカイブ管理を担当する。
"""

import logging
from pathlib import Path

from ptsu_code.memory.template import DEFAULT_TEMPLATE, is_empty

logger = logging.getLogger(__name__)


class SessionMemoryStorage:
    """Session Memory のファイルストレージ。

    current.md が常に最新のメモリ。
    セッション終了時に archive/<session_id>.md にコピーする。
    """

    def __init__(self, data_dir: Path, session_id: str) -> None:
        """初期化。

        Args:
            data_dir: データ保存ルートディレクトリ（例: ~/.ptsu）
            session_id: セッション識別子（例: 20260429_092300）
        """
        self.memory_dir: Path = data_dir / "session-memory"
        self.current_path: Path = self.memory_dir / "current.md"
        self.archive_dir: Path = self.memory_dir / "archive"
        self.session_id: str = session_id

    def load(self) -> str:
        """現在のメモリを読み込む。

        ファイルが存在しない場合はデフォルトテンプレートを返す。

        Returns:
            メモリ内容の文字列
        """
        if self.current_path.exists():
            return self.current_path.read_text(encoding="utf-8")
        return DEFAULT_TEMPLATE

    def save(self, content: str) -> None:
        """メモリをアトミックに書き込む。

        tmp ファイルに書いてから replace() で置き換えることで
        書き込み途中のクラッシュでも破損しないようにする。

        Args:
            content: 保存するメモリ内容
        """
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = self.memory_dir / ".current.tmp"
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(self.current_path)
        logger.debug("Session memory saved: %s", self.current_path)

    def archive(self) -> Path | None:
        """現在のメモリをアーカイブディレクトリへ保存する。

        テンプレートのみの場合（実際の内容なし）はスキップする。

        Returns:
            アーカイブファイルのパス。スキップした場合は None
        """
        if not self.current_path.exists():
            return None

        current_content = self.load()
        if is_empty(current_content):
            logger.debug("Session memory is empty (template only) — skipping archive")
            return None

        self.archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = self.archive_dir / f"{self.session_id}.md"
        archive_path.write_text(current_content, encoding="utf-8")
        logger.debug("Session memory archived: %s", archive_path)
        return archive_path

    def exists(self) -> bool:
        """メモリファイルが存在するか確認する。

        Returns:
            存在すれば True
        """
        return self.current_path.exists()

    def is_empty(self) -> bool:
        """メモリ内容がテンプレートのみかどうかを判定する。

        Returns:
            テンプレートと一致していれば True
        """
        if not self.exists():
            return True
        return is_empty(self.load())
