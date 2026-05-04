"""AgentRuntimeのテスト。"""

from unittest.mock import MagicMock, patch

import pytest

from ptsu_code.agent.providers.base import LLMResponse, LLMStreamChunk
from ptsu_code.agent.runtime import AgentRuntime, AgentSession, Message, RuntimeError


def _make_llm_response(content: str = "ok", tool_calls=None, finish_reason: str = "stop") -> LLMResponse:
    """テスト用LLMResponseを生成する。"""
    return LLMResponse(content=content, tool_calls=tool_calls, finish_reason=finish_reason)


def _make_runtime() -> tuple[AgentRuntime, MagicMock]:
    """テスト用AgentRuntimeとproviderモックを生成する。"""
    with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
        mock_provider = MagicMock()
        mock_cls.return_value = mock_provider
        runtime = AgentRuntime(provider="openai", api_key="test-key")
        return runtime, mock_provider


class TestMessage:
    """Messageのテスト。"""

    def test_to_dict_basic(self):
        """基本メッセージが辞書に変換されることを確認する。"""
        msg = Message(role="user", content="Hello")
        d = msg.to_dict()
        assert d["role"] == "user"
        assert d["content"] == "Hello"

    def test_to_dict_with_tool_calls(self):
        """tool_callsが含まれる辞書に変換されることを確認する。"""
        tc = [{"id": "call_1", "type": "function", "function": {"name": "t", "arguments": "{}"}}]
        msg = Message(role="assistant", content="", tool_calls=tc)
        d = msg.to_dict()
        assert "tool_calls" in d
        assert d["tool_calls"] == tc

    def test_to_dict_with_tool_call_id(self):
        """tool_call_idが含まれる辞書に変換されることを確認する。"""
        msg = Message(role="tool", content="result", tool_call_id="call_1", name="read_file")
        d = msg.to_dict()
        assert d["tool_call_id"] == "call_1"
        assert d["name"] == "read_file"

    def test_to_dict_no_optional_fields(self):
        """オプションフィールドがNoneのとき辞書に含まれないことを確認する。"""
        msg = Message(role="user", content="hi")
        d = msg.to_dict()
        assert "tool_calls" not in d
        assert "tool_call_id" not in d
        assert "name" not in d


class TestAgentSession:
    """AgentSessionのテスト。"""

    def test_add_message(self):
        """add_messageがメッセージを追加することを確認する。"""
        session = AgentSession()
        session.add_message("user", "Hello")
        assert len(session.messages) == 1
        assert session.messages[0].role == "user"
        assert session.messages[0].content == "Hello"

    def test_get_messages_returns_dicts(self):
        """get_messagesが辞書リストを返すことを確認する。"""
        session = AgentSession()
        session.add_message("user", "Hi")
        session.add_message("assistant", "Hello")
        messages = session.get_messages()
        assert len(messages) == 2
        assert all(isinstance(m, dict) for m in messages)

    def test_default_max_turns(self):
        """デフォルトmax_turnsが10であることを確認する。"""
        session = AgentSession()
        assert session.max_turns == 10

    def test_default_temperature(self):
        """デフォルトtemperatureがNone（モデルデフォルト使用）であることを確認する。"""
        session = AgentSession()
        assert session.temperature is None

    def test_add_message_with_kwargs(self):
        """kwargsを渡してadd_messageが動作することを確認する。"""
        session = AgentSession()
        tc = [{"id": "c1", "type": "function"}]
        session.add_message("assistant", "", tool_calls=tc)
        assert session.messages[0].tool_calls == tc


class TestAgentRuntimeInit:
    """AgentRuntime初期化のテスト。"""

    def test_init_openai_provider(self):
        """openaiプロバイダーでOpenAIProviderが作成されることを確認する。"""
        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_cls.return_value = MagicMock()
            runtime = AgentRuntime(provider="openai", api_key="key")
            assert runtime.provider_name == "openai"
            mock_cls.assert_called_once()

    def test_init_anthropic_provider(self):
        """anthropicプロバイダーでAnthropicProviderが作成されることを確認する。"""
        with patch("ptsu_code.agent.runtime.AnthropicProvider") as mock_cls:
            mock_cls.return_value = MagicMock()
            runtime = AgentRuntime(provider="anthropic", api_key="key")
            assert runtime.provider_name == "anthropic"
            mock_cls.assert_called_once()

    def test_init_no_openai_key_raises(self):
        """OpenAI APIキーがない場合RuntimeErrorが発生することを確認する。"""
        with patch("ptsu_code.agent.runtime.settings") as mock_settings:
            mock_settings.llm_provider = "openai"
            mock_settings.openai_api_key = None
            mock_settings.anthropic_api_key = None
            with pytest.raises(RuntimeError, match="OpenAI API key"):
                AgentRuntime(provider="openai", api_key=None)

    def test_init_no_anthropic_key_raises(self):
        """Anthropic APIキーがない場合RuntimeErrorが発生することを確認する。"""
        with patch("ptsu_code.agent.runtime.settings") as mock_settings:
            mock_settings.llm_provider = "anthropic"
            mock_settings.anthropic_api_key = None
            mock_settings.openai_api_key = None
            with pytest.raises(RuntimeError, match="Anthropic API key"):
                AgentRuntime(provider="anthropic", api_key=None)


class TestAgentRuntimeRunTurn:
    """AgentRuntime.run_turnのテスト。"""

    def test_run_turn_returns_llm_response(self):
        """run_turnがLLMResponseを返すことを確認する。"""
        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_provider = MagicMock()
            mock_provider.chat.return_value = _make_llm_response("Hello")
            mock_cls.return_value = mock_provider
            runtime = AgentRuntime(provider="openai", api_key="key")

            session = AgentSession()
            session.add_message("user", "Hi")
            result = runtime.run_turn(session)

            assert isinstance(result, LLMResponse)
            assert result.content == "Hello"

    def test_run_turn_passes_tools_when_registered(self):
        """ツール登録時にtoolsがchatに渡されることを確認する。"""
        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_provider = MagicMock()
            mock_provider.chat.return_value = _make_llm_response("ok")
            mock_cls.return_value = mock_provider
            runtime = AgentRuntime(provider="openai", api_key="key")

            session = AgentSession()
            session.add_message("user", "Hi")
            tool = MagicMock()
            tool.get_openai_schema.return_value = {"type": "function", "function": {"name": "test"}}
            session.tool_registry.register(tool)
            runtime.run_turn(session)

            call_kwargs = mock_provider.chat.call_args[1]
            assert call_kwargs.get("tools") is not None

    def test_run_turn_exception_raises_runtime_error(self):
        """API呼び出し失敗時にRuntimeErrorが発生することを確認する。"""
        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_provider = MagicMock()
            mock_provider.chat.side_effect = Exception("API error")
            mock_cls.return_value = mock_provider
            runtime = AgentRuntime(provider="openai", api_key="key")

            session = AgentSession()
            session.add_message("user", "Hi")
            with pytest.raises(RuntimeError):
                runtime.run_turn(session)


class TestAgentRuntimeRunLoop:
    """AgentRuntime.run_loopのテスト。"""

    def test_run_loop_simple_response(self):
        """ツール呼び出しなしの単純なレスポンスが返されることを確認する。"""
        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_provider = MagicMock()
            mock_provider.chat.return_value = _make_llm_response("Simple answer")
            mock_cls.return_value = mock_provider
            runtime = AgentRuntime(provider="openai", api_key="key")

            session = AgentSession()
            result = runtime.run_loop(session, "What is 2+2?")
            assert result == "Simple answer"

    def test_run_loop_adds_user_message(self):
        """user_messageがセッションに追加されることを確認する。"""
        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_provider = MagicMock()
            mock_provider.chat.return_value = _make_llm_response("ok")
            mock_cls.return_value = mock_provider
            runtime = AgentRuntime(provider="openai", api_key="key")

            session = AgentSession()
            runtime.run_loop(session, "Hello")
            assert any(m.role == "user" and m.content == "Hello" for m in session.messages)

    def test_run_loop_with_tool_call_then_final(self):
        """ツール呼び出し後に最終レスポンスが返されることを確認する。"""
        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_provider = MagicMock()
            tool_call = [{"id": "c1", "type": "function", "function": {"name": "t", "arguments": "{}"}}]
            mock_provider.chat.side_effect = [
                _make_llm_response("", tool_calls=tool_call, finish_reason="tool_calls"),
                _make_llm_response("Final answer"),
            ]
            mock_cls.return_value = mock_provider
            runtime = AgentRuntime(provider="openai", api_key="key")

            session = AgentSession()
            tool = MagicMock()
            tool.name = "t"
            tool.requires_approval = False
            tool_result = MagicMock()
            tool_result.success = True
            tool_result.output = "tool output"
            tool_result.error = ""
            tool.execute.return_value = tool_result
            session.tool_registry.register(tool)
            session.tool_registry.execute = MagicMock(return_value=tool_result)

            result = runtime.run_loop(session, "do something")
            assert result == "Final answer"

    def test_run_loop_max_turns_exceeded_raises(self):
        """最大ターン数を超えた場合RuntimeErrorが発生することを確認する。"""
        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_provider = MagicMock()
            tool_call = [{"id": "c1", "type": "function", "function": {"name": "t", "arguments": "{}"}}]
            mock_provider.chat.return_value = _make_llm_response(
                "", tool_calls=tool_call, finish_reason="tool_calls"
            )
            mock_cls.return_value = mock_provider
            runtime = AgentRuntime(provider="openai", api_key="key")

            session = AgentSession(max_turns=2)
            tool = MagicMock()
            tool.name = "t"
            tool.requires_approval = False
            tool_result = MagicMock()
            tool_result.success = True
            tool_result.output = "out"
            tool_result.error = ""
            session.tool_registry.register(tool)
            session.tool_registry.execute = MagicMock(return_value=tool_result)

            with pytest.raises(RuntimeError, match="Maximum turns"):
                runtime.run_loop(session, "infinite loop")


class TestAgentRuntimeExecuteToolCalls:
    """AgentRuntime.execute_tool_callsのテスト。"""

    def test_execute_tool_calls_success(self):
        """ツール呼び出しが成功することを確認する。"""
        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_cls.return_value = MagicMock()
            runtime = AgentRuntime(provider="openai", api_key="key")

            session = AgentSession()
            tool = MagicMock()
            tool.name = "my_tool"
            tool.requires_approval = False
            result_obj = MagicMock()
            result_obj.success = True
            result_obj.output = "tool output"
            result_obj.error = ""
            session.tool_registry.register(tool)
            session.tool_registry.execute = MagicMock(return_value=result_obj)

            tool_calls = [{"id": "c1", "type": "function", "function": {"name": "my_tool", "arguments": "{}"}}]
            results = runtime.execute_tool_calls(session, tool_calls)
            assert len(results) == 1
            assert results[0].role == "tool"
            assert results[0].content == "tool output"

    def test_execute_tool_calls_approval_denied(self):
        """ツール実行が拒否された場合のメッセージを確認する。"""
        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_cls.return_value = MagicMock()
            runtime = AgentRuntime(provider="openai", api_key="key")

            session = AgentSession()
            tool = MagicMock()
            tool.name = "dangerous_tool"
            tool.requires_approval = True
            session.tool_registry.register(tool)
            session.tool_registry.get = MagicMock(return_value=tool)
            session.approval_manager.needs_approval = MagicMock(return_value=True)

            tool_calls = [{"id": "c1", "type": "function", "function": {"name": "dangerous_tool", "arguments": "{}"}}]
            results = runtime.execute_tool_calls(session, tool_calls, request_approval_callback=lambda n, a: "n")
            assert len(results) == 1
            assert "rejected" in results[0].content.lower()

    def test_execute_tool_calls_approval_always(self):
        """常に承認するとツールがauto_approvedに追加されることを確認する。"""
        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_cls.return_value = MagicMock()
            runtime = AgentRuntime(provider="openai", api_key="key")

            session = AgentSession()
            tool = MagicMock()
            tool.name = "approvable_tool"
            tool.requires_approval = True
            result_obj = MagicMock()
            result_obj.success = True
            result_obj.output = "done"
            result_obj.error = ""
            session.tool_registry.register(tool)
            session.tool_registry.get = MagicMock(return_value=tool)
            session.tool_registry.execute = MagicMock(return_value=result_obj)
            mock_approval = MagicMock()
            mock_approval.needs_approval.return_value = True
            session.approval_manager = mock_approval

            tool_calls = [{"id": "c1", "type": "function", "function": {"name": "approvable_tool", "arguments": "{}"}}]
            runtime.execute_tool_calls(session, tool_calls, request_approval_callback=lambda n, a: "a")
            mock_approval.add_auto_approved_tool.assert_called_once_with("approvable_tool")

    def test_execute_tool_calls_no_approval_callback_rejects(self):
        """承認コールバックなしの場合ツール実行が拒否されることを確認する。"""
        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_cls.return_value = MagicMock()
            runtime = AgentRuntime(provider="openai", api_key="key")

            session = AgentSession()
            tool = MagicMock()
            tool.name = "needs_approval"
            tool.requires_approval = True
            session.tool_registry.register(tool)
            session.tool_registry.get = MagicMock(return_value=tool)
            session.approval_manager.needs_approval = MagicMock(return_value=True)

            tool_calls = [{"id": "c1", "type": "function", "function": {"name": "needs_approval", "arguments": "{}"}}]
            results = runtime.execute_tool_calls(session, tool_calls, request_approval_callback=None)
            assert "requires approval" in results[0].content.lower()

    def test_execute_tool_calls_exception_captured(self):
        """ツール実行で例外が発生した場合エラーメッセージが返されることを確認する。"""
        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_cls.return_value = MagicMock()
            runtime = AgentRuntime(provider="openai", api_key="key")

            session = AgentSession()
            tool = MagicMock()
            tool.name = "broken_tool"
            tool.requires_approval = False
            session.tool_registry.register(tool)
            session.tool_registry.get = MagicMock(return_value=tool)
            session.approval_manager.needs_approval = MagicMock(return_value=False)
            session.tool_registry.execute = MagicMock(side_effect=Exception("crash"))

            tool_calls = [{"id": "c1", "type": "function", "function": {"name": "broken_tool", "arguments": "{}"}}]
            results = runtime.execute_tool_calls(session, tool_calls)
            assert len(results) == 1
            assert "Error executing tool" in results[0].content

    def test_execute_tool_calls_with_progress_callback(self):
        """進捗コールバックが呼ばれることを確認する。"""
        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_cls.return_value = MagicMock()
            runtime = AgentRuntime(provider="openai", api_key="key")

            session = AgentSession()
            tool = MagicMock()
            tool.name = "t"
            tool.requires_approval = False
            result_obj = MagicMock()
            result_obj.success = True
            result_obj.output = "out"
            result_obj.error = ""
            session.tool_registry.register(tool)
            session.tool_registry.get = MagicMock(return_value=tool)
            session.approval_manager.needs_approval = MagicMock(return_value=False)
            session.tool_registry.execute = MagicMock(return_value=result_obj)

            progress_calls = []

            def progress_cb(name, args, status, **kwargs):
                progress_calls.append(status)

            tool_calls = [{"id": "c1", "type": "function", "function": {"name": "t", "arguments": "{}"}}]
            runtime.execute_tool_calls(session, tool_calls, show_progress_callback=progress_cb)
            assert "executing" in progress_calls
            assert "completed" in progress_calls


class TestAgentRuntimeRunTurnStream:
    """AgentRuntime.run_turn_streamのテスト。"""

    def test_run_turn_stream_yields_chunks(self):
        """ストリームチャンクが正しくyieldされることを確認する。"""
        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_provider = MagicMock()
            chunks = [
                LLMStreamChunk(content_delta="Hello"),
                LLMStreamChunk(is_final=True, final_response=_make_llm_response("Hello")),
            ]
            mock_provider.stream.return_value = iter(chunks)
            mock_cls.return_value = mock_provider
            runtime = AgentRuntime(provider="openai", api_key="key")

            session = AgentSession()
            session.add_message("user", "Hi")
            result = list(runtime.run_turn_stream(session))
            assert len(result) == 2

    def test_run_turn_stream_exception_raises_runtime_error(self):
        """ストリーム失敗時にRuntimeErrorが発生することを確認する。"""
        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_provider = MagicMock()
            mock_provider.stream.side_effect = Exception("stream error")
            mock_cls.return_value = mock_provider
            runtime = AgentRuntime(provider="openai", api_key="key")

            session = AgentSession()
            session.add_message("user", "Hi")
            with pytest.raises(RuntimeError):
                list(runtime.run_turn_stream(session))


class TestAgentRuntimeRunLoopStream:
    """AgentRuntime.run_loop_streamのテスト。"""

    def test_run_loop_stream_simple_response(self):
        """ストリーミングで単純なレスポンスが返されることを確認する。"""
        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_provider = MagicMock()
            final_resp = _make_llm_response("Streamed answer")
            chunks = [
                LLMStreamChunk(content_delta="Streamed "),
                LLMStreamChunk(content_delta="answer"),
                LLMStreamChunk(is_final=True, final_response=final_resp),
            ]
            mock_provider.stream.return_value = iter(chunks)
            mock_cls.return_value = mock_provider
            runtime = AgentRuntime(provider="openai", api_key="key")

            session = AgentSession()
            result = runtime.run_loop_stream(session, "Hi")
            assert result == "Streamed answer"

    def test_run_loop_stream_calls_stream_callback(self):
        """stream_callbackが正しく呼ばれることを確認する。"""
        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_provider = MagicMock()
            final_resp = _make_llm_response("ok")
            chunks = [
                LLMStreamChunk(content_delta="ok"),
                LLMStreamChunk(is_final=True, final_response=final_resp),
            ]
            mock_provider.stream.return_value = iter(chunks)
            mock_cls.return_value = mock_provider
            runtime = AgentRuntime(provider="openai", api_key="key")

            session = AgentSession()
            events = []
            runtime.run_loop_stream(session, "Hi", stream_callback=lambda e, c="": events.append(e))
            assert "start" in events
            assert "chunk" in events
            assert "end" in events

    def test_run_loop_stream_no_final_response_raises(self):
        """最終レスポンスがない場合RuntimeErrorが発生することを確認する。"""
        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_provider = MagicMock()
            mock_provider.stream.return_value = iter([LLMStreamChunk(content_delta="partial")])
            mock_cls.return_value = mock_provider
            runtime = AgentRuntime(provider="openai", api_key="key")

            session = AgentSession()
            with pytest.raises(RuntimeError, match="No final response"):
                runtime.run_loop_stream(session, "Hi")


class TestAgentRuntimeEvalLogger:
    """AgentRuntime の EvalLogger フックのテスト。"""

    def _make_runtime_with_logger(self):
        """EvalLogger 付き AgentRuntime とモックを返す。"""
        from ptsu_code.eval.logger import EvalLogger

        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_provider = MagicMock()
            mock_provider.default_model = "gpt-5-mini"
            mock_cls.return_value = mock_provider
            mock_logger = MagicMock(spec=EvalLogger)
            runtime = AgentRuntime(provider="openai", api_key="key", eval_logger=mock_logger)
            return runtime, mock_provider, mock_logger

    def test_start_eval_session_sets_session(self):
        """start_eval_session で _eval_session が生成されること。"""
        runtime, _, _ = self._make_runtime_with_logger()
        assert runtime._eval_session is None
        runtime.start_eval_session("sid-001")
        assert runtime._eval_session is not None
        assert runtime._eval_session.session_id == "sid-001"

    def test_start_eval_session_uuid_when_no_id(self):
        """session_id 省略時は UUID が自動生成されること。"""
        runtime, _, _ = self._make_runtime_with_logger()
        runtime.start_eval_session()
        assert runtime._eval_session is not None
        assert len(runtime._eval_session.session_id) > 0

    def test_finalize_eval_session_calls_save(self):
        """finalize_eval_session で EvalLogger.save が呼ばれること。"""
        runtime, _, mock_logger = self._make_runtime_with_logger()
        runtime.start_eval_session("sid-001")
        runtime.finalize_eval_session()
        mock_logger.save.assert_called_once()

    def test_finalize_clears_session(self):
        """finalize_eval_session 後は _eval_session が None になること。"""
        runtime, _, _ = self._make_runtime_with_logger()
        runtime.start_eval_session("sid-001")
        runtime.finalize_eval_session()
        assert runtime._eval_session is None

    def test_run_turn_records_turn_when_session_active(self):
        """start_eval_session 後の run_turn でターンが記録されること。"""
        runtime, mock_provider, _ = self._make_runtime_with_logger()
        mock_provider.chat.return_value = _make_llm_response("hello")

        runtime.start_eval_session("sid-001")
        session = AgentSession()
        session.add_message("user", "hi")
        runtime.run_turn(session)

        assert runtime._eval_session is not None
        assert runtime._eval_session.turn_count == 1

    def test_run_turn_no_logger_does_not_fail(self):
        """eval_logger なしの run_turn がエラーを起こさないこと。"""
        with patch("ptsu_code.agent.runtime.OpenAIProvider") as mock_cls:
            mock_provider = MagicMock()
            mock_provider.chat.return_value = _make_llm_response("ok")
            mock_cls.return_value = mock_provider
            runtime = AgentRuntime(provider="openai", api_key="key")

            session = AgentSession()
            session.add_message("user", "hi")
            result = runtime.run_turn(session)
            assert result.content == "ok"

    def test_turn_index_increments(self):
        """複数 run_turn でターンインデックスが増加すること。"""
        runtime, mock_provider, _ = self._make_runtime_with_logger()
        mock_provider.chat.return_value = _make_llm_response("ok")

        runtime.start_eval_session("sid-001")
        session = AgentSession()
        session.add_message("user", "hi")
        runtime.run_turn(session)
        session.add_message("assistant", "ok")
        session.add_message("user", "hi again")
        runtime.run_turn(session)

        assert runtime._eval_session.turn_count == 2
        assert runtime._eval_session.turns[0].turn_index == 0
        assert runtime._eval_session.turns[1].turn_index == 1
