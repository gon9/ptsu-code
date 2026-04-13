"""プロンプトのテスト。"""

from ptsu_code.agent.prompts import PromptTemplates, SystemPrompts


class TestSystemPrompts:
    """SystemPromptsのテストクラス。"""

    def test_coding_assistant(self):
        """コーディングアシスタントプロンプトのテスト。"""
        prompt = SystemPrompts.coding_assistant()

        assert "PTSU" in prompt
        assert "coding assistant" in prompt.lower()
        assert "read_file" in prompt
        assert "write_file" in prompt
        assert "execute_command" in prompt
        assert "grep_search" in prompt
        assert "find_files" in prompt
        assert "list_directory" in prompt

    def test_with_context_empty(self):
        """空のコンテキストでのテスト。"""
        base = "Base prompt"
        result = SystemPrompts.with_context(base, {})
        assert result == base

    def test_with_context_project_info(self):
        """プロジェクト情報付きコンテキストのテスト。"""
        base = "Base prompt"
        context = {"project_info": "Python project"}
        result = SystemPrompts.with_context(base, context)

        assert "Base prompt" in result
        assert "Project Context" in result
        assert "Python project" in result

    def test_with_context_multiple(self):
        """複数のコンテキスト情報のテスト。"""
        base = "Base prompt"
        context = {
            "project_info": "Python project",
            "current_task": "Add feature X",
            "constraints": "Use Python 3.12",
        }
        result = SystemPrompts.with_context(base, context)

        assert "Project Context" in result
        assert "Current Task" in result
        assert "Constraints" in result


class TestPromptTemplates:
    """PromptTemplatesのテストクラス。"""

    def test_code_review_request_basic(self):
        """基本的なコードレビューリクエストのテスト。"""
        prompt = PromptTemplates.code_review_request("src/main.py")

        assert "review" in prompt.lower()
        assert "src/main.py" in prompt

    def test_code_review_request_with_focus(self):
        """焦点付きコードレビューリクエストのテスト。"""
        prompt = PromptTemplates.code_review_request("src/main.py", "performance")

        assert "src/main.py" in prompt
        assert "performance" in prompt

    def test_bug_fix_request_basic(self):
        """基本的なバグ修正リクエストのテスト。"""
        prompt = PromptTemplates.bug_fix_request("Null pointer exception")

        assert "bug" in prompt.lower()
        assert "Null pointer exception" in prompt

    def test_bug_fix_request_with_file(self):
        """ファイル指定付きバグ修正リクエストのテスト。"""
        prompt = PromptTemplates.bug_fix_request("Null pointer exception", "src/main.py")

        assert "Null pointer exception" in prompt
        assert "src/main.py" in prompt

    def test_feature_request_basic(self):
        """基本的な機能追加リクエストのテスト。"""
        prompt = PromptTemplates.feature_request("Add user authentication")

        assert "feature" in prompt.lower()
        assert "Add user authentication" in prompt

    def test_feature_request_with_requirements(self):
        """要件付き機能追加リクエストのテスト。"""
        requirements = ["Use JWT tokens", "Support OAuth2"]
        prompt = PromptTemplates.feature_request("Add user authentication", requirements)

        assert "Add user authentication" in prompt
        assert "JWT tokens" in prompt
        assert "OAuth2" in prompt

    def test_refactoring_request(self):
        """リファクタリングリクエストのテスト。"""
        prompt = PromptTemplates.refactoring_request("UserService", "improve testability")

        assert "refactor" in prompt.lower()
        assert "UserService" in prompt
        assert "improve testability" in prompt

    def test_test_generation_request_default(self):
        """デフォルトのテスト生成リクエストのテスト。"""
        prompt = PromptTemplates.test_generation_request("UserService")

        assert "test" in prompt.lower()
        assert "UserService" in prompt
        assert "unit" in prompt

    def test_test_generation_request_integration(self):
        """統合テスト生成リクエストのテスト。"""
        prompt = PromptTemplates.test_generation_request("UserService", "integration")

        assert "integration" in prompt
        assert "UserService" in prompt
