"""Observation Masking のテスト。"""

from ptsu_code.agent.context import mask_observations


def _msg(role: str, content: str = "hello", **kwargs):
    """テスト用メッセージ生成ヘルパー。"""
    return {"role": role, "content": content, **kwargs}


class TestMaskObservations:
    """mask_observations() のテスト。"""

    def test_no_tool_messages_unchanged(self):
        """toolメッセージがない場合は変更なし。"""
        msgs = [_msg("system", "sys"), _msg("user", "hi"), _msg("assistant", "ok")]
        result = mask_observations(msgs)
        assert result == msgs

    def test_tool_messages_within_keep_recent_unchanged(self):
        """toolメッセージがkeep_recent以下なら変更なし。"""
        msgs = [
            _msg("user", "hi"),
            _msg("assistant", "calling tool", tool_calls=[{"id": "c1"}]),
            _msg("tool", "result1", tool_call_id="c1", name="read_file"),
            _msg("tool", "result2", tool_call_id="c2", name="grep_search"),
        ]
        result = mask_observations(msgs, keep_recent=6)
        assert result == msgs

    def test_old_tool_messages_masked(self):
        """古いtoolメッセージがマスクされることを確認する。"""
        msgs = [
            _msg("user", "hi"),
            _msg("assistant", ""),
            _msg("tool", "A" * 500, tool_call_id="c1", name="read_file"),
            _msg("tool", "B" * 300, tool_call_id="c2", name="list_dir"),
            _msg("assistant", "more"),
            _msg("tool", "C" * 100, tool_call_id="c3", name="grep_search"),
            _msg("assistant", "done"),
            _msg("tool", "D" * 50, tool_call_id="c4", name="find_files"),
        ]
        result = mask_observations(msgs, keep_recent=2)

        assert "[Observation masked: read_file (500 chars)]" == result[2]["content"]
        assert "[Observation masked: list_dir (300 chars)]" == result[3]["content"]

        assert result[5]["content"] == "C" * 100
        assert result[7]["content"] == "D" * 50

    def test_non_tool_messages_never_masked(self):
        """user/assistant/systemメッセージは決してマスクされない。"""
        msgs = [
            _msg("system", "S" * 1000),
            _msg("user", "U" * 1000),
            _msg("assistant", "A" * 1000),
            _msg("tool", "T1", tool_call_id="c1", name="t1"),
            _msg("tool", "T2", tool_call_id="c2", name="t2"),
            _msg("tool", "T3", tool_call_id="c3", name="t3"),
            _msg("tool", "T4", tool_call_id="c4", name="t4"),
            _msg("tool", "T5", tool_call_id="c5", name="t5"),
            _msg("tool", "T6", tool_call_id="c6", name="t6"),
            _msg("tool", "T7", tool_call_id="c7", name="t7"),
        ]
        result = mask_observations(msgs, keep_recent=2)

        assert result[0]["content"] == "S" * 1000
        assert result[1]["content"] == "U" * 1000
        assert result[2]["content"] == "A" * 1000

    def test_preserves_tool_call_id_and_name(self):
        """マスクされたメッセージもtool_call_idとnameは保持する。"""
        msgs = [
            _msg("tool", "long result", tool_call_id="c1", name="read_file"),
            _msg("tool", "recent", tool_call_id="c2", name="grep"),
        ]
        result = mask_observations(msgs, keep_recent=1)

        masked = result[0]
        assert masked["tool_call_id"] == "c1"
        assert masked["name"] == "read_file"
        assert "Observation masked" in masked["content"]

    def test_original_messages_not_mutated(self):
        """元のメッセージリストが変更されないことを確認する。"""
        original_content = "original long text"
        msgs = [
            _msg("tool", original_content, tool_call_id="c1", name="t1"),
            _msg("tool", "recent", tool_call_id="c2", name="t2"),
        ]
        mask_observations(msgs, keep_recent=1)

        assert msgs[0]["content"] == original_content

    def test_keep_recent_zero_masks_all(self):
        """keep_recent=0 で全てのtoolメッセージがマスクされる。"""
        msgs = [
            _msg("user", "hi"),
            _msg("tool", "result", tool_call_id="c1", name="t1"),
        ]
        result = mask_observations(msgs, keep_recent=0)

        assert "Observation masked" in result[1]["content"]

    def test_empty_messages(self):
        """空リストに対してエラーが出ないこと。"""
        assert mask_observations([]) == []

    def test_tool_without_name_uses_fallback(self):
        """nameが無いtoolメッセージでもフォールバックでマスクされる。"""
        msgs = [
            _msg("tool", "result", tool_call_id="c1"),
            _msg("tool", "recent", tool_call_id="c2", name="t2"),
        ]
        result = mask_observations(msgs, keep_recent=1)

        assert "[Observation masked: tool (6 chars)]" == result[0]["content"]
