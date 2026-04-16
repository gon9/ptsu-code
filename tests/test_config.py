"""設定管理のテスト。"""

from pathlib import Path

import pytest

from ptsu_code.config import PROVIDER_MODELS, Settings, get_model


class TestSettings:
    """Settingsクラスのテスト。"""

    def test_default_settings(self, monkeypatch, tmp_path):
        """デフォルト設定が正しいことを確認する。"""
        # 環境変数をクリア
        monkeypatch.delenv("PTSU_OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("PTSU_ANTHROPIC_API_KEY", raising=False)
        # .envファイルが存在しないディレクトリに移動
        monkeypatch.chdir(tmp_path)

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

    def test_model_tier_defaults(self):
        """モデルティアのデフォルト値が正しいことを確認する。"""
        settings = Settings()
        assert settings.openai_model_fast == "gpt-5-mini"
        assert settings.openai_model_smart == "gpt-4o"
        assert settings.anthropic_model_fast == "claude-haiku-4-5"
        assert settings.anthropic_model_smart == "claude-sonnet-4-5"

    @pytest.mark.parametrize("env_var,attr", [
        ("PTSU_OPENAI_MODEL_FAST", "openai_model_fast"),
        ("PTSU_OPENAI_MODEL_SMART", "openai_model_smart"),
        ("PTSU_ANTHROPIC_MODEL_FAST", "anthropic_model_fast"),
        ("PTSU_ANTHROPIC_MODEL_SMART", "anthropic_model_smart"),
    ])
    def test_model_tier_env_override(self, monkeypatch, env_var, attr):
        """環境変数でモデルティアをオーバーライドできることを確認する。"""
        monkeypatch.setenv(env_var, "custom-model")
        settings = Settings()
        assert getattr(settings, attr) == "custom-model"


class TestProviderModels:
    """PROVIDER_MODELSとget_model()のテスト。"""

    def test_provider_models_has_openai(self):
        """PROVIDER_MODELSにopenaiが含まれることを確認する。"""
        assert "openai" in PROVIDER_MODELS
        assert "fast" in PROVIDER_MODELS["openai"]
        assert "smart" in PROVIDER_MODELS["openai"]

    def test_provider_models_has_anthropic(self):
        """PROVIDER_MODELSにanthropicが含まれることを確認する。"""
        assert "anthropic" in PROVIDER_MODELS
        assert "fast" in PROVIDER_MODELS["anthropic"]
        assert "smart" in PROVIDER_MODELS["anthropic"]

    @pytest.mark.parametrize("provider,tier,expected", [
        ("openai", "fast", "gpt-5-mini"),
        ("openai", "smart", "gpt-4o"),
        ("anthropic", "fast", "claude-haiku-4-5"),
        ("anthropic", "smart", "claude-sonnet-4-5"),
    ])
    def test_get_model_returns_correct_model(self, provider, tier, expected):
        """get_model()が正しいモデル名を返すことを確認する。"""
        assert get_model(provider, tier) == expected

    def test_get_model_defaults_to_fast(self):
        """get_model()のtierデフォルトがfastであることを確認する。"""
        assert get_model("openai") == "gpt-5-mini"

    def test_get_model_unknown_provider_falls_back_to_openai(self):
        """未知のプロバイダーはopenaiにフォールバックすることを確認する。"""
        result = get_model("unknown_provider", "fast")
        assert result == "gpt-5-mini"
