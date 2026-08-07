"""
app.py

Streamlit frontend for the Autonomous Data Analyst Agent.
"""

import streamlit as st
import tempfile
import os
from sqlalchemy import create_engine
from logging_config import configure_logging
import jwt
import datetime
from typing import Optional

from agents import inspect_database_schema
from graph import run_workflow
from guardrails import validate_sql
from uploads import create_engine_from_uploaded

st.set_page_config(page_title="Autonomous Data Analyst Agent", layout="wide")

# Authentication
# If `JWT_SECRET` is set, require a JWT-based login with credentials from env (AUTH_USER/AUTH_PASS).
# Otherwise fall back to simple `STREAMLIT_AUTH_TOKEN` if provided.
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGO = os.getenv("JWT_ALGO", "HS256")
AUTH_USER = os.getenv("AUTH_USER", "admin")
AUTH_PASS = os.getenv("AUTH_PASS", "password")

def create_token(username: str, expires_minutes: int = 60) -> str:
    payload = {
        "sub": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=expires_minutes),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return payload.get("sub")
    except Exception:
        return None

STREAMLIT_AUTH_TOKEN = os.getenv("STREAMLIT_AUTH_TOKEN")

if JWT_SECRET:
    # Simple login form that issues a JWT stored in session state
    if "jwt_token" not in st.session_state:
        st.session_state["jwt_token"] = None

    if st.session_state.get("jwt_token"):
        user = verify_token(st.session_state["jwt_token"])
        if not user:
            st.session_state["jwt_token"] = None

    if not st.session_state.get("jwt_token"):
        st.sidebar.subheader("Login")
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Sign in"):
            if username == AUTH_USER and password == AUTH_PASS:
                token = create_token(username)
                st.session_state["jwt_token"] = token
                st.experimental_rerun()
            else:
                st.sidebar.error("Invalid credentials")
        # stop until login
        st.stop()
    else:
        user = verify_token(st.session_state["jwt_token"])
        st.sidebar.markdown(f"Signed in as **{user}**")
        if st.sidebar.button("Sign out"):
            st.session_state["jwt_token"] = None
            st.experimental_rerun()
else:
    # fallback simple token-based auth
    AUTH_TOKEN = STREAMLIT_AUTH_TOKEN
    if AUTH_TOKEN:
        token = st.sidebar.text_input("App token", type="password")
        if not token:
            st.stop()
        if token != AUTH_TOKEN:
            st.sidebar.error("Invalid token")
            st.stop()

# configure logging
configure_logging()

st.title("Autonomous Data Analyst Agent")

st.markdown(
    """
    This app connects to a PostgreSQL database, validates read-only SQL, executes queries,
    displays results, and shows a simple visualization and summary.
    """
)

st.sidebar.header("Query options")
user_query = st.sidebar.text_input("Ask a business question", value="Show sales by region")
manual_sql = st.sidebar.text_area("Or paste a SELECT SQL query", value="", height=170)

# Optional: allow users to upload a SQLite database file and run queries against it
uploaded_file = st.sidebar.file_uploader(
    "Upload database or dataset (.db, .sqlite, .csv, .parquet, .sql)",
    type=["db", "sqlite", "sqlite3", "csv", "parquet", "sql"],
)
uploaded_engine = None
uploaded_temp_path = None
if uploaded_file is not None:
    try:
        uploaded_engine, uploaded_temp_path = create_engine_from_uploaded(uploaded_file, uploaded_file.name)
        st.sidebar.success(f"Uploaded and loaded: {uploaded_file.name}")
    except Exception as exc:
        st.sidebar.error(f"Failed to process upload: {exc}")

with st.expander("Database schema"):
    st.text(inspect_database_schema(uploaded_engine))

run_query_button = st.sidebar.button("Run query")

if run_query_button:
    try:
        if manual_sql.strip():
            validated_sql = validate_sql(manual_sql)
            workflow = run_workflow(user_query="", manual_sql=validated_sql, engine_override=uploaded_engine)
        else:
            workflow = run_workflow(user_query=user_query, manual_sql=None, engine_override=uploaded_engine)

        st.subheader("Generated SQL")
        st.code(workflow["sql"], language="sql")

        st.subheader("Query results")
        st.dataframe(workflow["dataframe"])

        figures = workflow.get("figures")
        if not figures and workflow.get("figure") is not None:
            figures = [workflow.get("figure")]

        if figures:
            st.subheader("Visualizations")
            for figure in figures:
                st.plotly_chart(figure, use_container_width=True)

        st.subheader("Plan")
        plan = workflow.get("plan")
        if plan:
            steps = plan.get("steps", [])
            for s in steps:
                st.markdown(f"- {s}")

        # Chart metadata and CSV export
        chart_type = workflow.get("chart_type")
        if chart_type:
            st.caption(f"Chart type: {chart_type}")

        df = workflow.get("dataframe")
        if df is not None and not df.empty:
            csv = df.to_csv(index=False)
            st.download_button(label="Download CSV", data=csv, file_name="query_results.csv", mime="text/csv")

        st.subheader("Insights")
        insights = workflow.get("insights", "")
        # Render insights as markdown bullets when possible
        if isinstance(insights, str) and ("- " in insights or "\n" in insights):
            # try to convert lines starting with - into markdown list
            lines = [l.strip() for l in insights.splitlines() if l.strip()]
            for line in lines:
                if line.startswith("- "):
                    st.markdown(line)
                else:
                    st.write(line)
        else:
            st.write(insights)
    except Exception as exc:
        st.error(f"Error: {exc}")
