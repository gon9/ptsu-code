"""設定管理のテスト。"""

from pathlib import Path

import pytest

from ptsu_code.config import Settings


class TestSettings:
    """Settingsクラスのテスト。"""

    def test_default_settings(self):
        """デフォルト設定が正しいことを確認する。"""
        settings = Settings()
        assert settings.app_name == "ptsu"
        assert settings.version == "0.1.0"
        assert settings.verbose is False
        assert settings.openai_api_key == ""
        assert isinstance(settings.history_dir, Path)

    @pytest.mark.parametrize(
        ("env_vars", "expected_attr", "expected_value"),
        [
            ({"PTSU_APP_NAME": "custom"}, "app_name", "custom"),
            ({"PTSU_VERBOSE": "true"}, "verbose", True),
            ({"PTSU_VERBOSE": "false"}, "verbose", False),
            ({"PTSU_OPENAI_API_KEY": "test-key"}, "openai_api_key", "test-key"),
        ],
    )
    def test_settings_from_env(self, monkeypatch, env_vars, expected_attr, expected_value):
        """環境変数から設定が読み込まれることを確認する。"""
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        settings = Settings()
        assert getattr(settings, expected_attr) == expected_value

    def test_history_dir_is_path(self):
        """history_dirがPathオブジェクトであることを確認する。"""
        settings = Settings()
        assert isinstance(settings.history_dir, Path)
        assert ".ptsu" in str(settings.history_dir)
        assert "history" in str(settings.history_dir)
