"""
app.py

Premium Streamlit frontend for the Autonomous Data Analyst Agent.
Dark glassmorphism theme, tabbed results, query history, pipeline badges.
"""

import os
import time
import datetime
from typing import Optional

import streamlit as st
import jwt
from sqlalchemy import create_engine

from logging_config import configure_logging
from agents import inspect_database_schema
from graph import run_workflow
from guardrails import validate_sql
from uploads import create_engine_from_uploaded

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Data Analyst Agent · BI Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

configure_logging()

# ── Premium CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* ── Root & body ── */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .stApp {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #0d1117 100%);
        min-height: 100vh;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #161b22 0%, #0d1117 100%);
        border-right: 1px solid rgba(99,102,241,0.2);
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.5rem;
    }

    /* ── Main container ── */
    .main .block-container {
        padding: 1.5rem 2rem;
        max-width: 1400px;
    }

    /* ── Glass card ── */
    .glass-card {
        background: rgba(22, 27, 34, 0.85);
        border: 1px solid rgba(99,102,241,0.25);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.25rem;
        backdrop-filter: blur(12px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05);
        transition: border-color 0.3s ease;
    }
    .glass-card:hover { border-color: rgba(99,102,241,0.5); }

    /* ── Hero header ── */
    .hero-header {
        background: linear-gradient(135deg, rgba(99,102,241,0.15) 0%, rgba(168,85,247,0.15) 100%);
        border: 1px solid rgba(99,102,241,0.3);
        border-radius: 20px;
        padding: 2rem 2.5rem;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .hero-title {
        font-size: 2.4rem;
        font-weight: 700;
        background: linear-gradient(135deg, #818cf8 0%, #a78bfa 50%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0 0 0.5rem 0;
        letter-spacing: -0.02em;
    }
    .hero-subtitle {
        color: rgba(148,163,184,0.9);
        font-size: 1rem;
        font-weight: 400;
        margin: 0;
    }

    /* ── Pipeline badge strip ── */
    .pipeline-strip {
        display: flex;
        gap: 0.4rem;
        flex-wrap: wrap;
        margin: 1rem 0;
        align-items: center;
    }
    .pipeline-badge {
        background: rgba(99,102,241,0.12);
        border: 1px solid rgba(99,102,241,0.3);
        border-radius: 999px;
        padding: 0.3rem 0.75rem;
        font-size: 0.72rem;
        font-weight: 500;
        color: #a5b4fc;
        white-space: nowrap;
    }
    .pipeline-badge.active {
        background: rgba(99,102,241,0.3);
        border-color: #818cf8;
        color: #e0e7ff;
    }
    .pipeline-arrow {
        color: rgba(99,102,241,0.4);
        font-size: 0.8rem;
    }

    /* ── Metric cards ── */
    .metric-row {
        display: flex;
        gap: 1rem;
        margin-bottom: 1.25rem;
        flex-wrap: wrap;
    }
    .metric-card {
        flex: 1;
        min-width: 140px;
        background: rgba(22,27,34,0.9);
        border: 1px solid rgba(99,102,241,0.2);
        border-radius: 12px;
        padding: 1rem 1.25rem;
        text-align: center;
    }
    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: #818cf8;
        line-height: 1;
        margin-bottom: 0.25rem;
    }
    .metric-label {
        font-size: 0.75rem;
        color: rgba(148,163,184,0.7);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* ── SQL code block ── */
    .sql-block {
        background: #0d1117;
        border: 1px solid rgba(99,102,241,0.25);
        border-radius: 10px;
        padding: 1rem 1.25rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        color: #a5b4fc;
        white-space: pre-wrap;
        overflow-x: auto;
    }

    /* ── Guardrail error ── */
    .guardrail-error {
        background: rgba(239,68,68,0.1);
        border: 1px solid rgba(239,68,68,0.4);
        border-radius: 10px;
        padding: 0.9rem 1.25rem;
        color: #fca5a5;
        font-size: 0.9rem;
    }

    /* ── Insight bullets ── */
    .insight-bullet {
        border-left: 3px solid #818cf8;
        padding-left: 1rem;
        margin-bottom: 0.6rem;
        color: #cbd5e1;
        font-size: 0.92rem;
        line-height: 1.6;
    }

    /* ── History item ── */
    .history-item {
        background: rgba(99,102,241,0.07);
        border: 1px solid rgba(99,102,241,0.15);
        border-radius: 8px;
        padding: 0.6rem 0.9rem;
        margin-bottom: 0.4rem;
        cursor: pointer;
        transition: background 0.2s ease;
        font-size: 0.83rem;
        color: #94a3b8;
    }
    .history-item:hover {
        background: rgba(99,102,241,0.15);
        color: #c7d2fe;
    }

    /* ── Status dot ── */
    .status-dot {
        display: inline-block;
        width: 8px; height: 8px;
        border-radius: 50%;
        margin-right: 6px;
        animation: pulse 2s infinite;
    }
    .status-dot.online { background: #22c55e; }
    .status-dot.offline { background: #ef4444; }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: transparent;
        border-bottom: 1px solid rgba(99,102,241,0.2);
        padding-bottom: 0;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(99,102,241,0.08) !important;
        border: 1px solid rgba(99,102,241,0.2) !important;
        border-radius: 8px 8px 0 0 !important;
        color: #94a3b8 !important;
        font-weight: 500;
        padding: 0.5rem 1.1rem !important;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(99,102,241,0.25) !important;
        border-color: #818cf8 !important;
        color: #e0e7ff !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        border: none;
        border-radius: 10px;
        color: white;
        font-weight: 600;
        letter-spacing: 0.02em;
        padding: 0.55rem 1.4rem;
        transition: all 0.25s ease;
        box-shadow: 0 4px 15px rgba(99,102,241,0.3);
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(99,102,241,0.5);
    }
    .stButton > button:active { transform: translateY(0); }

    /* ── Inputs ── */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: rgba(13,17,23,0.8) !important;
        border: 1px solid rgba(99,102,241,0.3) !important;
        border-radius: 8px !important;
        color: #e2e8f0 !important;
        font-family: 'Inter', sans-serif;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #818cf8 !important;
        box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0d1117; }
    ::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.4); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,0.7); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Authentication ────────────────────────────────────────────────────────────
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGO = os.getenv("JWT_ALGO", "HS256")
AUTH_USER = os.getenv("AUTH_USER", "admin")
AUTH_PASS = os.getenv("AUTH_PASS", "password")
STREAMLIT_AUTH_TOKEN = os.getenv("STREAMLIT_AUTH_TOKEN")


def _create_token(username: str, expires_minutes: int = 60) -> str:
    payload = {
        "sub": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=expires_minutes),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def _verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return payload.get("sub")
    except Exception:
        return None


if JWT_SECRET:
    if "jwt_token" not in st.session_state:
        st.session_state["jwt_token"] = None
    if st.session_state.get("jwt_token"):
        if not _verify_token(st.session_state["jwt_token"]):
            st.session_state["jwt_token"] = None
    if not st.session_state.get("jwt_token"):
        st.sidebar.markdown("### 🔐 Login")
        username = st.sidebar.text_input("Username", key="auth_user")
        password = st.sidebar.text_input("Password", type="password", key="auth_pass")
        if st.sidebar.button("Sign in", key="signin_btn"):
            if username == AUTH_USER and password == AUTH_PASS:
                st.session_state["jwt_token"] = _create_token(username)
                st.rerun()
            else:
                st.sidebar.error("❌ Invalid credentials")
        st.stop()
    else:
        user = _verify_token(st.session_state["jwt_token"])
        st.sidebar.markdown(f"✅ Signed in as **{user}**")
        if st.sidebar.button("Sign out", key="signout_btn"):
            st.session_state["jwt_token"] = None
            st.rerun()
elif STREAMLIT_AUTH_TOKEN:
    token = st.sidebar.text_input("🔑 App token", type="password", key="auth_token_input")
    if not token:
        st.stop()
    if token != STREAMLIT_AUTH_TOKEN:
        st.sidebar.error("❌ Invalid token")
        st.stop()

# ── Session State Defaults ────────────────────────────────────────────────────
if "query_history" not in st.session_state:
    st.session_state["query_history"] = []
if "last_result" not in st.session_state:
    st.session_state["last_result"] = None

# ── Hero Header ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero-header">
      <h1 class="hero-title">🤖 Autonomous Data Analyst Agent</h1>
      <p class="hero-subtitle">
        Ask business questions in plain English · AI-powered SQL · Interactive charts · Executive insights
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 Query")
    user_query = st.text_area(
        "Ask a business question",
        value="Show total sales by region",
        height=90,
        key="user_query_input",
        placeholder="e.g. Show monthly revenue trend by product category",
    )
    manual_sql = st.text_area(
        "Or paste a SELECT query directly",
        value="",
        height=120,
        key="manual_sql_input",
        placeholder="SELECT ... FROM ... WHERE ...",
    )

    st.markdown("---")
    st.markdown("## 📁 Data Source")
    uploaded_file = st.file_uploader(
        "Upload a database or dataset",
        type=["db", "sqlite", "sqlite3", "csv", "parquet", "sql"],
        help="Supports SQLite (.db/.sqlite), CSV, Parquet, and SQL dump files",
    )

    uploaded_engine = None
    uploaded_temp_path = None
    if uploaded_file is not None:
        try:
            from uploads import create_engine_from_uploaded
            uploaded_engine, uploaded_temp_path = create_engine_from_uploaded(
                uploaded_file, uploaded_file.name
            )
            st.success(f"✅ Loaded: `{uploaded_file.name}`")
        except Exception as exc:
            st.error(f"❌ Upload failed: {exc}")

    # DB status indicator
    st.markdown("---")
    st.markdown("## ⚙️ Database Status")
    try:
        schema_preview = inspect_database_schema(uploaded_engine)
        is_connected = schema_preview and "No schema" not in schema_preview
        dot_class = "online" if is_connected else "offline"
        dot_label = "Connected" if is_connected else "No DB / Upload a file"
    except Exception:
        dot_class = "offline"
        dot_label = "Connection error"

    st.markdown(
        f'<span class="status-dot {dot_class}"></span> <small style="color:#94a3b8">{dot_label}</small>',
        unsafe_allow_html=True,
    )

    with st.expander("📐 Schema Inspector", expanded=False):
        st.text(inspect_database_schema(uploaded_engine))

    st.markdown("---")
    run_btn = st.button("▶ Run Analysis", use_container_width=True, key="run_btn")

    # Query history
    if st.session_state["query_history"]:
        st.markdown("---")
        st.markdown("## 🕓 Recent Queries")
        for i, hist in enumerate(reversed(st.session_state["query_history"][-8:])):
            st.markdown(
                f'<div class="history-item">#{len(st.session_state["query_history"]) - i} · {hist}</div>',
                unsafe_allow_html=True,
            )

# ── Pipeline Badge Strip ──────────────────────────────────────────────────────
_PIPELINE_NODES = [
    ("🔎", "Schema"),
    ("🧠", "Planner"),
    ("📝", "SQL Specialist"),
    ("🛡️", "Guardrail"),
    ("🗄️", "Executor"),
    ("📊", "Visualizer"),
    ("💡", "Insights"),
]

pipeline_html = '<div class="pipeline-strip">'
for i, (icon, label) in enumerate(_PIPELINE_NODES):
    pipeline_html += f'<span class="pipeline-badge">{icon} {label}</span>'
    if i < len(_PIPELINE_NODES) - 1:
        pipeline_html += '<span class="pipeline-arrow">→</span>'
pipeline_html += "</div>"
st.markdown(pipeline_html, unsafe_allow_html=True)

# ── Main Analysis Area ────────────────────────────────────────────────────────
if run_btn:
    query_text = manual_sql.strip() if manual_sql.strip() else user_query.strip()
    if not query_text:
        st.warning("⚠️ Please enter a question or SQL query.")
    else:
        with st.spinner("🤖 Running multi-agent pipeline…"):
            try:
                t_start = time.perf_counter()
                if manual_sql.strip():
                    validated = validate_sql(manual_sql.strip())
                    result = run_workflow(
                        user_query=user_query or "Manual SQL",
                        manual_sql=validated,
                        engine_override=uploaded_engine,
                    )
                else:
                    result = run_workflow(
                        user_query=user_query,
                        manual_sql=None,
                        engine_override=uploaded_engine,
                    )
                elapsed = result.get("elapsed_ms", (time.perf_counter() - t_start) * 1000)

                # Save to history
                hist_entry = manual_sql.strip() if manual_sql.strip() else user_query.strip()
                if hist_entry and (
                    not st.session_state["query_history"]
                    or st.session_state["query_history"][-1] != hist_entry
                ):
                    st.session_state["query_history"].append(hist_entry)
                st.session_state["last_result"] = result

            except Exception as exc:
                st.error(f"❌ Pipeline error: {exc}")
                result = None

        if result:
            df = result.get("dataframe")
            rows = result.get("rows_returned", len(df) if df is not None else 0)
            figures = result.get("figures") or (
                [result["figure"]] if result.get("figure") else []
            )
            validation_error = result.get("validation_error")

            # ── Metrics ──────────────────────────────────────────────────────
            st.markdown(
                f"""
                <div class="metric-row">
                  <div class="metric-card">
                    <div class="metric-value">{rows:,}</div>
                    <div class="metric-label">Rows Returned</div>
                  </div>
                  <div class="metric-card">
                    <div class="metric-value">{len(figures)}</div>
                    <div class="metric-label">Charts Generated</div>
                  </div>
                  <div class="metric-card">
                    <div class="metric-value">{elapsed:.0f}<small style="font-size:1rem">ms</small></div>
                    <div class="metric-label">Pipeline Time</div>
                  </div>
                  <div class="metric-card">
                    <div class="metric-value">{'✓' if not validation_error else '✗'}</div>
                    <div class="metric-label">SQL Guardrail</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # ── Tabs ─────────────────────────────────────────────────────────
            tab_sql, tab_data, tab_charts, tab_insights, tab_plan = st.tabs(
                ["📝 SQL", "📋 Data", "📊 Charts", "💡 Insights", "🗺️ Plan"]
            )

            with tab_sql:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                if validation_error:
                    st.markdown(
                        f'<div class="guardrail-error">🛡️ <strong>Guardrail blocked:</strong> {validation_error}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    sql_code = result.get("sql") or result.get("generated_sql") or "—"
                    st.markdown(f'<div class="sql-block">{sql_code}</div>', unsafe_allow_html=True)
                    st.code(sql_code, language="sql")
                    if sql_code and sql_code != "—":
                        st.download_button(
                            "⬇ Download SQL",
                            data=sql_code,
                            file_name="query.sql",
                            mime="text/plain",
                        )
                st.markdown("</div>", unsafe_allow_html=True)

            with tab_data:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                if df is not None and not df.empty:
                    st.dataframe(df, use_container_width=True, height=420)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "⬇ Download CSV",
                        data=csv,
                        file_name="query_results.csv",
                        mime="text/csv",
                    )
                else:
                    st.info("No data returned.")
                st.markdown("</div>", unsafe_allow_html=True)

            with tab_charts:
                if figures:
                    chart_types = result.get("chart_types", [])
                    for i, fig in enumerate(figures):
                        label = chart_types[i].replace("_", " ").title() if i < len(chart_types) else f"Chart {i+1}"
                        st.markdown(f"**{label}**")
                        st.plotly_chart(fig, use_container_width=True, key=f"chart_{i}")
                else:
                    st.info("No visualizations generated for this query.")

            with tab_insights:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                insights_text = result.get("insights", "")
                if insights_text:
                    lines = [l.strip() for l in insights_text.splitlines() if l.strip()]
                    for line in lines:
                        clean = line.lstrip("-•* ").strip()
                        if clean:
                            st.markdown(
                                f'<div class="insight-bullet">{clean}</div>',
                                unsafe_allow_html=True,
                            )
                else:
                    st.info("No insights generated.")
                st.markdown("</div>", unsafe_allow_html=True)

            with tab_plan:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                plan = result.get("plan", {})
                steps = result.get("planned_steps") or plan.get("steps", [])

                col1, col2 = st.columns(2)
                with col1:
                    sql_req = "✅ Yes" if plan.get("sql_required") else "❌ No"
                    st.metric("SQL Required", sql_req)
                with col2:
                    viz_req = "✅ Yes" if plan.get("visualization_required") else "❌ No"
                    st.metric("Visualization Required", viz_req)

                st.markdown("#### Execution Steps")
                for j, step in enumerate(steps, 1):
                    st.markdown(
                        f'<div class="pipeline-badge active" style="display:inline-block;margin-bottom:0.4rem">'
                        f'{j}. {step}</div>',
                        unsafe_allow_html=True,
                    )
                st.markdown("</div>", unsafe_allow_html=True)

# ── Empty State ───────────────────────────────────────────────────────────────
elif st.session_state["last_result"] is None:
    st.markdown(
        """
        <div class="glass-card" style="text-align:center;padding:3rem 2rem">
          <div style="font-size:3rem;margin-bottom:1rem">🤖</div>
          <h3 style="color:#818cf8;margin-bottom:0.5rem">Ready for Analysis</h3>
          <p style="color:#64748b;max-width:480px;margin:0 auto">
            Enter a business question in the sidebar, upload a database file, and click
            <strong style="color:#a5b4fc">▶ Run Analysis</strong> to start the multi-agent pipeline.
          </p>
          <br>
          <p style="color:#475569;font-size:0.85rem">
            💡 Try: <em>"Show total revenue by product category"</em> or
            <em>"Which region had the highest sales in Q1?"</em>
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
