"""
agents.py

AI agent implementations for the Autonomous Data Analyst pipeline.
Supports NVIDIA NIM (primary) and OpenAI (fallback) via LangChain.
Falls back to deterministic heuristics when no LLM is configured.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import plotly.express as px
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from config import get_llm, engine
from guardrails import validate_sql

logger = logging.getLogger(__name__)


# ── LLM Invocation ────────────────────────────────────────────────────────────

def ask_llm(prompt: str, system: str | None = None) -> str:
    """Invoke the configured LangChain LLM with an optional system message.

    Returns the text content of the response, or raises RuntimeError if no
    LLM is configured.
    """
    llm = get_llm()
    if llm is None:
        raise RuntimeError(
            "No LLM API key configured. Set NVIDIA_API_KEY or OPENAI_API_KEY in .env"
        )

    from langchain_core.messages import HumanMessage, SystemMessage

    messages = []
    if system:
        messages.append(SystemMessage(content=system))
    messages.append(HumanMessage(content=prompt))

    response = llm.invoke(messages)
    return response.content.strip()


def _llm_available() -> bool:
    return get_llm() is not None


# ── Schema Agent ──────────────────────────────────────────────────────────────

def schema_agent(engine_override=None) -> str:
    """Inspect the database engine and return a human-readable schema string."""
    eng = engine_override or engine
    if eng is None:
        return "No database engine available."

    lines: list[str] = []
    try:
        inspector = inspect(eng)
        for table in inspector.get_table_names():
            lines.append(f"Table: {table}")
            for column in inspector.get_columns(table):
                lines.append(f"  - {column['name']} ({column['type']})")
            # Include a small sample to help the LLM infer real values
            try:
                quoted_table = _quote_identifier(table)
                with eng.connect() as conn:
                    sample = pd.read_sql(text(f"SELECT * FROM {quoted_table} LIMIT 3"), conn)
                if not sample.empty:
                    lines.append("  Sample rows:")
                    for row in sample.to_dict(orient="records"):
                        lines.append(f"    - {row}")
            except Exception:
                pass
    except Exception as exc:
        logger.warning("Schema inspection failed: %s", exc)
        return "No schema available. The table structure could not be inspected."

    return "\n".join(lines) if lines else "No schema available."


def inspect_database_schema(engine_override=None) -> str:
    """Public alias for schema_agent."""
    return schema_agent(engine_override)


# ── Planner Agent ─────────────────────────────────────────────────────────────

def planner_agent(user_query: str, schema_text: str | None = None) -> Dict[str, Any]:
    """Return an execution plan dict with keys: sql_required, visualization_required, steps.

    Tries the LLM first; falls back to keyword heuristics.
    """
    q = user_query.lower()
    heuristic_sql = any(k in q for k in [
        "show", "list", "count", "sum", "average", "sales", "revenue",
        "select", "by", "group", "how many", "total", "top", "best", "worst",
    ])
    heuristic_viz = any(k in q for k in [
        "chart", "plot", "visual", "trend", "compare", "by", "over time",
        "monthly", "quarterly", "yearly", "distribution",
    ])

    prompt_path = Path("prompts/planner_prompt.txt")
    if _llm_available() and prompt_path.exists():
        raw_template = prompt_path.read_text(encoding="utf-8")
        prompt = (
            raw_template
            .replace("{USER_REQUEST}", user_query)
            .replace("{SCHEMA}", schema_text or "No schema available.")
        )
        try:
            raw = ask_llm(prompt)
            # Strip markdown code fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
            raw = re.sub(r"\s*```$", "", raw.strip())
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and "sql_required" in parsed:
                logger.info("Planner (LLM): %s", parsed)
                return parsed
        except Exception as exc:
            logger.warning("Planner LLM parse failed (%s); using heuristic", exc)

    steps: list[str] = []
    if heuristic_sql:
        steps += ["Generate SQL", "Execute query"]
    if heuristic_viz:
        steps.append("Create visualization")
    steps.append("Generate insights")

    plan = {
        "sql_required": heuristic_sql,
        "visualization_required": heuristic_viz,
        "steps": steps,
    }
    logger.info("Planner (heuristic): %s", plan)
    return plan


# ── SQL Specialist Agent ──────────────────────────────────────────────────────

def sql_specialist(user_query: str, schema_text: str, engine_override=None) -> str:
    """Generate a read-only SELECT statement for the given user request.

    Uses the LLM when available; falls back to deterministic heuristics.
    """
    prompt_path = Path("prompts/sql_prompt.txt")
    if _llm_available() and prompt_path.exists():
        raw_template = prompt_path.read_text(encoding="utf-8")
        prompt = (
            raw_template
            .replace("{SCHEMA}", schema_text)
            .replace("{USER_REQUEST}", user_query)
        )
        try:
            sql = ask_llm(prompt)
            # Strip markdown code fences
            sql = re.sub(r"^```(?:sql)?\s*", "", sql.strip())
            sql = re.sub(r"\s*```$", "", sql.strip())
            logger.info("SQL Specialist (LLM) produced: %s", sql[:120])
            return validate_sql(sql)
        except Exception as exc:
            logger.warning("SQL Specialist LLM failed (%s); using heuristic", exc)

    return generate_sql_from_query(user_query, engine_override=engine_override)


# ── SQL Executor ──────────────────────────────────────────────────────────────

def run_query(sql: str) -> pd.DataFrame:
    return run_query_safe(sql)


def run_query_safe(
    sql: str,
    engine_override=None,
    max_rows: int = 1000,
    timeout_ms: int = 5000,
) -> pd.DataFrame:
    """Execute validated SQL safely with row limits and statement timeout."""
    if not sql:
        raise ValueError("No SQL provided for execution.")

    eng = engine_override or engine
    if eng is None:
        raise RuntimeError("No database engine available.")

    normalized = sql.strip().lower()
    sql_exec = sql.strip() if "limit" in normalized else f"{sql.strip()} LIMIT {max_rows}"

    with eng.connect() as conn:
        trans = conn.begin()
        try:
            try:
                conn.execute(text("SET LOCAL statement_timeout = :ms"), {"ms": timeout_ms})
            except OperationalError:
                pass  # SQLite and older DBs don't support this
            df = pd.read_sql(text(sql_exec), conn)
            trans.commit()
            return df
        except Exception:
            trans.rollback()
            raise


# ── Visualization Agent ───────────────────────────────────────────────────────

def visualization_agent(dataframe: pd.DataFrame) -> Dict[str, Any]:
    """Choose appropriate Plotly charts based on the result DataFrame."""
    if dataframe is None or dataframe.empty:
        return {"figure": None, "figures": [], "chart_type": "", "chart_types": []}

    numeric_cols = dataframe.select_dtypes(include="number").columns.tolist()
    category_cols = dataframe.select_dtypes(exclude="number").columns.tolist()
    datetime_cols = dataframe.select_dtypes(
        include=["datetime64[ns]", "datetime64[ns, UTC]"]
    ).columns.tolist()

    figures: list[Any] = []
    chart_types: list[str] = []

    _PLOTLY_TEMPLATE = "plotly_dark"

    if category_cols and numeric_cols:
        x, y = category_cols[0], numeric_cols[0]
        fig = px.bar(
            dataframe, x=x, y=y,
            title=f"{_label(y)} by {_label(x)}",
            labels={x: _label(x), y: _label(y)},
            template=_PLOTLY_TEMPLATE,
            color=x,
        )
        fig.update_layout(showlegend=False)
        figures.append(fig)
        chart_types.append("bar")

        if len(numeric_cols) > 1:
            fig2 = px.line(
                dataframe, x=x, y=numeric_cols,
                title=f"{', '.join(_label(c) for c in numeric_cols)} by {_label(x)}",
                template=_PLOTLY_TEMPLATE,
            )
            figures.append(fig2)
            chart_types.append("line")

    if datetime_cols and numeric_cols:
        x = datetime_cols[0]
        fig = px.line(
            dataframe, x=x, y=numeric_cols,
            title=f"{', '.join(_label(c) for c in numeric_cols)} over Time",
            template=_PLOTLY_TEMPLATE,
        )
        figures.append(fig)
        chart_types.append("time_series")

    if not figures and len(numeric_cols) >= 2:
        fig = px.line(
            dataframe, y=numeric_cols,
            title="Numeric Trends",
            labels={c: _label(c) for c in numeric_cols},
            template=_PLOTLY_TEMPLATE,
        )
        figures.append(fig)
        chart_types.append("line")

        fig2 = px.scatter(
            dataframe, x=numeric_cols[0], y=numeric_cols[1],
            title=f"{_label(numeric_cols[1])} vs {_label(numeric_cols[0])}",
            template=_PLOTLY_TEMPLATE,
        )
        figures.append(fig2)
        chart_types.append("scatter")

    if not figures and len(numeric_cols) == 1:
        fig = px.histogram(
            dataframe, x=numeric_cols[0],
            title=f"Distribution of {_label(numeric_cols[0])}",
            nbins=20, template=_PLOTLY_TEMPLATE,
        )
        figures.append(fig)
        chart_types.append("histogram")

        fig2 = px.box(
            dataframe, y=numeric_cols[0],
            title=f"Outliers — {_label(numeric_cols[0])}",
            template=_PLOTLY_TEMPLATE,
        )
        figures.append(fig2)
        chart_types.append("box")

    if figures:
        return {
            "figure": figures[0],
            "figures": figures,
            "chart_type": chart_types[0],
            "chart_types": chart_types,
        }
    return {"figure": None, "figures": [], "chart_type": "", "chart_types": []}


def create_chart(dataframe: pd.DataFrame):
    """Simple single-chart helper (backward compat)."""
    result = visualization_agent(dataframe)
    return result.get("figure")


# ── Insights Agent ────────────────────────────────────────────────────────────

def insights_agent(dataframe: pd.DataFrame) -> str:
    """Generate an executive insight summary from query results."""
    if dataframe is None or dataframe.empty:
        return "No rows returned by the query."

    prompt_path = Path("prompts/insights_prompt.txt")
    sample = dataframe.head(10).to_dict(orient="records")
    cols = ", ".join(dataframe.columns.tolist())

    if _llm_available() and prompt_path.exists():
        raw_template = prompt_path.read_text(encoding="utf-8")
        prompt = (
            raw_template
            .replace("{COLUMNS}", cols)
            .replace("{SAMPLE_ROWS}", str(sample))
        )
        try:
            insights = ask_llm(prompt)
            if insights:
                logger.info("Insights (LLM): generated")
                return insights.strip()
        except Exception as exc:
            logger.warning("Insights LLM failed (%s); using fallback", exc)

    return _fallback_insights(dataframe)


def generate_insights(dataframe: pd.DataFrame) -> str:
    """Public alias used by some legacy callers."""
    return insights_agent(dataframe)


# ── Heuristic SQL Generator ───────────────────────────────────────────────────

def generate_sql_from_query(user_query: str, engine_override=None) -> str:
    q = user_query.strip()
    if not q:
        return "SELECT * FROM information_schema.tables LIMIT 100"

    schema_text = inspect_database_schema(engine_override)
    tables = _parse_schema_text(schema_text)
    if not tables:
        raise ValueError("Unable to inspect database schema for SQL generation.")

    table = _best_table_for_query(q, tables)
    quoted_table = _quote_identifier(table)
    columns = tables[table]
    group_col = _find_group_column(q, columns)
    agg_fn, agg_col = _aggregation_for_query(q, columns)

    if agg_fn == "COUNT" and group_col:
        qg = _quote_identifier(group_col)
        return (
            f"SELECT {qg}, COUNT(*) AS total_count "
            f"FROM {quoted_table} GROUP BY {qg} ORDER BY total_count DESC LIMIT 100"
        )
    if agg_fn == "COUNT":
        return f"SELECT COUNT(*) AS total_count FROM {quoted_table} LIMIT 100"
    if agg_fn in {"SUM", "AVG", "MIN", "MAX"} and agg_col:
        qa = _quote_identifier(agg_col)
        alias = f"{agg_fn.lower()}_{agg_col.replace(' ', '_')}"
        if group_col:
            qg = _quote_identifier(group_col)
            return (
                f"SELECT {qg}, {agg_fn}({qa}) AS {alias} "
                f"FROM {quoted_table} GROUP BY {qg} ORDER BY {alias} DESC LIMIT 100"
            )
        return f"SELECT {agg_fn}({qa}) AS total_{agg_col.replace(' ', '_')} FROM {quoted_table} LIMIT 100"

    if re.search(r"\b(by|according to|per|group)\b", q.lower()) and group_col:
        qg = _quote_identifier(group_col)
        return (
            f"SELECT {qg}, COUNT(*) AS total_count "
            f"FROM {quoted_table} GROUP BY {qg} ORDER BY total_count DESC LIMIT 100"
        )

    cols_sql = _serialize_column_list(columns)
    return f"SELECT {cols_sql} FROM {quoted_table} ORDER BY 1 LIMIT 100"


# ── Private Helpers ───────────────────────────────────────────────────────────

def _label(col: str) -> str:
    return col.replace("_", " ").title()


def _quote_identifier(name: str) -> str:
    if not name:
        return name
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        return '"' + name.replace('"', '""') + '"'
    return name


def _serialize_column_list(columns: list[tuple[str, str]], limit: int = 8) -> str:
    names = [_quote_identifier(col) for col, _ in columns][:limit]
    return ", ".join(names) if names else "*"


def _normalize_text(t: str) -> str:
    return re.sub(r"[^A-Za-z0-9_ ]+", " ", t).lower()


def _is_numeric_type(col_type: str) -> bool:
    return any(t in col_type.lower() for t in ["int", "real", "float", "numeric", "decimal", "money"])


def _parse_schema_text(schema_text: str) -> dict[str, list[tuple[str, str]]]:
    tables: dict[str, list[tuple[str, str]]] = {}
    current: str | None = None
    for line in schema_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("table:"):
            current = line[len("Table:"):].strip()
            tables[current] = []
        elif line.startswith("-") and current is not None:
            parts = line[1:].strip().split("(", 1)
            col_name = parts[0].strip()
            col_type = parts[1].rstrip(")").strip() if len(parts) > 1 else ""
            tables[current].append((col_name, col_type))
    return tables


def _best_table_for_query(user_query: str, tables: dict[str, list[tuple[str, str]]]) -> str:
    q = user_query.lower()
    if not tables:
        raise ValueError("No tables available in schema.")
    for table in tables:
        if table.lower() in q:
            return table
    for table, cols in tables.items():
        if any(col.lower() in q for col, _ in cols):
            return table
    for table, cols in tables.items():
        if any(_is_numeric_type(typ) for _, typ in cols):
            return table
    return next(iter(tables))


def _find_column_match(
    user_query: str,
    columns: list[tuple[str, str]],
    numeric_only: bool = False,
) -> str | None:
    q = _normalize_text(user_query)
    names = [col for col, typ in columns if not numeric_only or _is_numeric_type(typ)]
    for col in names:
        if col.lower() in q:
            return col
    tokens = set(q.split())
    for col in names:
        if set(re.findall(r"\w+", col.lower())) & tokens:
            return col
    if numeric_only:
        return names[0] if names else None
    non_numeric = [col for col, typ in columns if not _is_numeric_type(typ)]
    return non_numeric[0] if non_numeric else (names[0] if names else None)


def _find_group_column(user_query: str, columns: list[tuple[str, str]]) -> str | None:
    q = _normalize_text(user_query)
    phrases = re.findall(r"\bby ([a-z0-9_ ]+?)(?:$|,|;| and | or | for | with )", q)
    for phrase in phrases:
        phrase = phrase.strip()
        if phrase:
            col = _find_column_match(phrase, columns, numeric_only=False)
            if col:
                return col
    return _find_column_match(user_query, columns, numeric_only=False)


def _find_preferred_numeric_column(
    user_query: str,
    columns: list[tuple[str, str]],
    require_keyword_match: bool = False,
) -> str | None:
    q = _normalize_text(user_query)
    numeric = [col for col, typ in columns if _is_numeric_type(typ)]
    if not numeric:
        return None
    for col in numeric:
        if col.lower() in q:
            return col
    pref_kws = ["revenue", "profit", "amount", "sales", "quantity", "price", "total", "cost", "units", "income"]
    match = next((col for col in numeric if any(kw in col.lower() for kw in pref_kws)), None)
    if match:
        return match
    if require_keyword_match:
        return None
    return numeric[0]


def _aggregation_for_query(
    user_query: str,
    columns: list[tuple[str, str]],
) -> tuple[str | None, str | None]:
    q = _normalize_text(user_query)
    if re.search(r"\b(avg|average|mean)\b", q):
        return ("AVG", _find_preferred_numeric_column(q, columns))
    if re.search(r"\b(sum|total|revenue|profit|amount|sales|quantity|price|cost|income|units)\b", q):
        col = _find_column_match(q, columns, numeric_only=True) or _find_preferred_numeric_column(q, columns, require_keyword_match=True)
        return ("SUM", col) if col else ("COUNT", None)
    if re.search(r"\b(max|maximum|highest)\b", q):
        col = _find_preferred_numeric_column(q, columns)
        return ("MAX", col) if col else (None, None)
    if re.search(r"\b(min|minimum|lowest)\b", q):
        col = _find_preferred_numeric_column(q, columns)
        return ("MIN", col) if col else (None, None)
    if re.search(r"\b(count|how many|number of|frequency|distribution)\b", q):
        return ("COUNT", None)
    if re.search(r"\b(by|according to|per|between|group)\b", q):
        return ("COUNT", None)
    return (None, None)


def _fallback_insights(dataframe: pd.DataFrame) -> str:
    rows = len(dataframe)
    columns = list(dataframe.columns)
    lines = [
        "📊 **Query Insights**",
        f"- **Rows returned:** {rows}",
        f"- **Columns:** {', '.join(columns)}",
    ]
    numeric_cols = dataframe.select_dtypes(include="number").columns.tolist()
    for col in numeric_cols:
        vals = dataframe[col].dropna()
        if vals.empty:
            continue
        lines.append(
            f"- **{_label(col)}:** min {vals.min():,.2f} · max {vals.max():,.2f} · "
            f"mean {vals.mean():,.2f} · median {vals.median():,.2f}"
        )
    category_cols = dataframe.select_dtypes(exclude="number").columns.tolist()
    for col in category_cols:
        top = dataframe[col].mode()
        if not top.empty:
            lines.append(f"- **Most common {_label(col)}:** {top.iloc[0]}")
    if numeric_cols:
        top_col = max(numeric_cols, key=lambda c: dataframe[c].sum(skipna=True))
        lines.append(
            f"- **Highest aggregate column:** {_label(top_col)} "
            f"(total: {dataframe[top_col].sum(skipna=True):,.2f})"
        )
    return "\n".join(lines)
