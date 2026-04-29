"""SessionMemoryStorage のユニットテスト。"""

import pytest

from ptsu_code.memory.storage import SessionMemoryStorage
from ptsu_code.memory.template import DEFAULT_TEMPLATE


class TestSessionMemoryStorage:
    """SessionMemoryStorage のテスト。"""

    @pytest.fixture()
    def storage(self, tmp_path):
        """テスト用ストレージ。"""
        return SessionMemoryStorage(tmp_path, "20260429_120000")

    def test_load_returns_template_when_file_missing(self, storage) -> None:
        """ファイルが存在しない場合デフォルトテンプレートを返すこと。"""
        content = storage.load()
        assert content == DEFAULT_TEMPLATE

    def test_save_creates_file(self, storage) -> None:
        """save がファイルを作成すること。"""
        storage.save("# test content")
        assert storage.current_path.exists()
        assert storage.current_path.read_text(encoding="utf-8") == "# test content"

    def test_save_overwrites_existing(self, storage) -> None:
        """save が既存ファイルを上書きすること。"""
        storage.save("first")
        storage.save("second")
        assert storage.load() == "second"

    def test_save_is_atomic(self, storage) -> None:
        """save がアトミックに書き込むこと（tmp ファイルが残らないこと）。"""
        storage.save("content")
        tmp = storage.memory_dir / ".current.tmp"
        assert not tmp.exists()
        assert storage.current_path.exists()

    def test_exists_returns_false_when_missing(self, storage) -> None:
        """ファイルが存在しない場合 exists が False を返すこと。"""
        assert storage.exists() is False

    def test_exists_returns_true_after_save(self, storage) -> None:
        """save 後に exists が True を返すこと。"""
        storage.save("x")
        assert storage.exists() is True

    def test_is_empty_returns_true_when_missing(self, storage) -> None:
        """ファイルが存在しない場合 is_empty が True を返すこと。"""
        assert storage.is_empty() is True

    def test_is_empty_returns_true_when_template_only(self, storage) -> None:
        """テンプレートのみの場合 is_empty が True を返すこと。"""
        storage.save(DEFAULT_TEMPLATE)
        assert storage.is_empty() is True

    def test_is_empty_returns_false_when_has_content(self, storage) -> None:
        """実際の内容がある場合 is_empty が False を返すこと。"""
        storage.save("# Session Title\nreal content\n")
        assert storage.is_empty() is False

    def test_archive_creates_file(self, storage) -> None:
        """archive がアーカイブファイルを作成すること。"""
        storage.save("# Session Title\nsome content")
        archived = storage.archive()
        assert archived is not None
        assert archived.exists()
        assert "20260429_120000" in archived.name

    def test_archive_returns_none_when_empty(self, storage) -> None:
        """テンプレートのみの場合 archive が None を返すこと。"""
        storage.save(DEFAULT_TEMPLATE)
        result = storage.archive()
        assert result is None

    def test_archive_returns_none_when_no_file(self, storage) -> None:
        """ファイルが存在しない場合 archive が None を返すこと。"""
        result = storage.archive()
        assert result is None

    def test_load_after_save_roundtrip(self, storage) -> None:
        """save した内容を load で取得できること。"""
        content = "# My Session\nsome useful data"
        storage.save(content)
        assert storage.load() == content
