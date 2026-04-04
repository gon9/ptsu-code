"""__main__.pyのテスト。"""

from unittest.mock import patch


def test_main_module_can_be_imported():
    """__main__.pyがインポート可能であることを確認する。"""
    with patch("ptsu_code.cli.app.main"):
        import ptsu_code.__main__

        assert ptsu_code.__main__ is not None
