"""PTSU Evaluation Dashboard — Streamlit アプリ。

起動方法:
    uv run streamlit run src/ptsu_code/eval/dashboard.py
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import streamlit as st
except ImportError:
    print("streamlit が未インストールです。以下を実行してください:")
    print("  uv add --optional eval streamlit pandas")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("pandas が未インストールです。以下を実行してください:")
    print("  uv add --optional eval streamlit pandas")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parents[3]))

from ptsu_code.eval.logger import EvalLogger
from ptsu_code.eval.models import SessionMetrics

st.set_page_config(
    page_title="PTSU Eval Dashboard",
    page_icon="🤖",
    layout="wide",
)


@st.cache_data(ttl=30)
def load_sessions() -> list[SessionMetrics]:
    """セッションデータを読み込む（30秒キャッシュ）。"""
    logger = EvalLogger()
    return logger.load_all()


def sessions_to_df(sessions: list[SessionMetrics]) -> pd.DataFrame:
    """セッションリストを DataFrame に変換する。"""
    rows = []
    for s in sessions:
        rows.append({
            "session_id": s.session_id[:8],
            "started_at": s.started_at[:19].replace("T", " "),
            "provider": s.provider,
            "model": s.model,
            "turns": s.turn_count,
            "input_tokens": s.total_input_tokens,
            "output_tokens": s.total_output_tokens,
            "cost_usd": round(s.total_cost_usd, 6),
        })
    return pd.DataFrame(rows)


def turns_to_df(sessions: list[SessionMetrics]) -> pd.DataFrame:
    """全ターンを DataFrame に変換する。"""
    rows = []
    for s in sessions:
        for t in s.turns:
            rows.append({
                "session_id": s.session_id[:8],
                "timestamp": t.timestamp[:19].replace("T", " "),
                "provider": t.provider,
                "model": t.model,
                "input_tokens": t.input_tokens,
                "output_tokens": t.output_tokens,
                "cost_usd": round(t.cost_usd, 6),
                "latency_ms": round(t.latency_ms, 1),
                "had_tool_calls": t.had_tool_calls,
            })
    return pd.DataFrame(rows)


def main() -> None:
    """ダッシュボードのメイン関数。"""
    st.title("🤖 PTSU Eval Dashboard")
    st.caption("セッションメトリクス・コスト・レイテンシの可視化")

    if st.button("🔄 データを再読み込み"):
        st.cache_data.clear()

    sessions = load_sessions()

    if not sessions:
        st.info("まだセッションデータがありません。`ptsu chat` を実行してください。")
        st.code("ptsu chat")
        return

    session_df = sessions_to_df(sessions)
    turn_df = turns_to_df(sessions)

    total_cost = sum(s.total_cost_usd for s in sessions)
    total_turns = sum(s.turn_count for s in sessions)
    total_tokens = sum(s.total_input_tokens + s.total_output_tokens for s in sessions)
    avg_latency = turn_df["latency_ms"].mean() if not turn_df.empty else 0.0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("総セッション数", len(sessions))
    col2.metric("総ターン数", total_turns)
    col3.metric("総トークン数", f"{total_tokens:,}")
    col4.metric("推定コスト (USD)", f"${total_cost:.4f}")

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📊 プロバイダー別コスト")
        if not turn_df.empty:
            cost_by_provider = (
                turn_df.groupby("provider")["cost_usd"].sum().reset_index()
            )
            cost_by_provider.columns = ["Provider", "Cost (USD)"]
            st.bar_chart(cost_by_provider.set_index("Provider"))
        else:
            st.info("データなし")

    with col_right:
        st.subheader("⚡ ターンレイテンシ分布 (ms)")
        if not turn_df.empty:
            st.bar_chart(
                turn_df["latency_ms"].value_counts(bins=10).sort_index()
            )
            st.caption(f"平均: {avg_latency:.0f} ms")
        else:
            st.info("データなし")

    st.divider()
    st.subheader("🗂 モデル別トークン使用量")
    if not turn_df.empty:
        token_by_model = (
            turn_df.groupby("model")[["input_tokens", "output_tokens"]]
            .sum()
            .reset_index()
        )
        st.bar_chart(token_by_model.set_index("model"))

    st.divider()
    st.subheader("📋 セッション一覧")
    st.dataframe(
        session_df.sort_values("started_at", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("🔍 ターン詳細")
    if not turn_df.empty:
        st.dataframe(
            turn_df.sort_values("timestamp", ascending=False).head(100),
            use_container_width=True,
            hide_index=True,
        )


if __name__ == "__main__":
    main()
