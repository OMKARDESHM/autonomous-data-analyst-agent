"""
agents.py

Simple query generation, execution, visualization, and insight utilities.
"""

import re
from typing import Optional, Dict, Any
import json
from pathlib import Path

from sqlalchemy.exc import OperationalError

from sqlalchemy import inspect, text
import pandas as pd
import plotly.express as px

from config import engine, OPENAI_API_KEY, OPENAI_MODEL
import openai
from guardrails import validate_sql


def ask_llm(prompt: str) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set. Set OPENAI_API_KEY to use ChatGPT.")
    response = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that only outputs valid PostgreSQL SELECT queries "
                    "or concise executive business summaries when requested. Do not include explanations."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=800,
    )
    return response.choices[0].message["content"].strip()


def planner_agent(user_query: str, schema_text: str | None = None) -> Dict[str, Any]:
    """Return a simple execution plan indicating whether SQL and visualization are required.

    Attempts to use the LLM to return JSON with the shape:
    {"sql_required": bool, "visualization_required": bool, "steps": [str, ...]}

    Falls back to a lightweight heuristic when the LLM is unavailable or parsing fails.
    """
    heuristic_sql = any(k in user_query.lower() for k in ["show", "list", "count", "sum", "average", "sales", "revenue", "select", "by", "group", "how many"])
    heuristic_viz = any(k in user_query.lower() for k in ["chart", "plot", "visual", "trend", "compare", "by"])

    prompt_path = Path("prompts/planner_prompt.txt")
    if OPENAI_API_KEY and prompt_path.exists():
        raw_template = prompt_path.read_text()
        prompt = raw_template.replace("{USER_REQUEST}", user_query)
        prompt = prompt.replace("{SCHEMA}", schema_text or "No schema available.")
        try:
            raw = ask_llm(prompt)
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and "sql_required" in parsed:
                return parsed
        except Exception:
            pass

    steps = []
    if heuristic_sql:
        steps.append("Generate SQL")
        steps.append("Execute SQL")
    if heuristic_viz:
        steps.append("Create chart")
    steps.append("Generate insights")

    return {"sql_required": heuristic_sql, "visualization_required": heuristic_viz, "steps": steps}


def sql_specialist(user_query: str, schema_text: str, engine_override=None) -> str:
    """Generate a single read-only PostgreSQL SELECT based on the user request and schema.

    Uses the LLM when available; falls back to `generate_sql_from_query` heuristics.
    """
    prompt_path = Path("prompts/sql_prompt.txt")
    if OPENAI_API_KEY and prompt_path.exists():
        raw_template = prompt_path.read_text()
        prompt = raw_template.replace("{SCHEMA}", schema_text).replace("{USER_REQUEST}", user_query)
        try:
            sql = ask_llm(prompt)
            return validate_sql(sql)
        except Exception:
            pass

    # fallback to existing heuristic generator
    return generate_sql_from_query(user_query, engine_override=engine_override)


def inspect_database_schema(engine_override=None) -> str:
    return schema_agent(engine_override)


def schema_agent(engine_override=None) -> str:
    """Scan the current database engine and return a schema description for the SQL specialist."""
    eng = engine_override or engine
    lines = []
    try:
        inspector = inspect(eng)
        for table in inspector.get_table_names():
            lines.append(f"Table: {table}")
            for column in inspector.get_columns(table):
                lines.append(f"  - {column['name']} ({column['type']})")
            # include a small sample of rows to help the LLM infer column usage
            try:
                quoted_table = _quote_identifier(table)
                with eng.connect() as conn:
                    sample = pd.read_sql(text(f"SELECT * FROM {quoted_table} LIMIT 5"), conn)
                if not sample.empty:
                    lines.append("  Sample rows:")
                    for row in sample.to_dict(orient="records"):
                        lines.append(f"    - {row}")
            except Exception:
                pass
    except Exception:
        lines = []

    if lines:
        return "\n".join(lines)

    return "No schema available. The table structure could not be inspected."


def _parse_schema_text(schema_text: str) -> dict[str, list[tuple[str, str]]]:
    tables = {}
    current_table = None
    for line in schema_text.splitlines():
        line = line.strip()
        if not line:
            continue
        line_lower = line.lower()
        if line_lower.startswith("table:"):
            current_table = line[len("Table:"):].strip()
            tables[current_table] = []
        elif line.startswith("-") and current_table is not None:
            parts = line[1:].strip().split("(", 1)
            col_name = parts[0].strip()
            col_type = parts[1].rstrip(")").strip() if len(parts) > 1 else ""
            tables[current_table].append((col_name, col_type))

    return tables


def _best_table_for_query(user_query: str, tables: dict[str, list[tuple[str, str]]]) -> str:
    query = user_query.lower()
    if not tables:
        raise ValueError("No tables available in schema to generate SQL.")

    # Prefer explicit table mentions
    for table in tables:
        if table.lower() in query:
            return table

    # Prefer a table with a matching column name mention
    for table, cols in tables.items():
        if any(col.lower() in query for col, _ in cols):
            return table

    # Otherwise prefer a table with a numeric column for aggregations, or just the first table
    for table, cols in tables.items():
        if any("int" in typ.lower() or "real" in typ.lower() or "float" in typ.lower() or "numeric" in typ.lower() or "decimal" in typ.lower() for _, typ in cols):
            return table

    return next(iter(tables))


def _quote_identifier(name: str) -> str:
    if not name:
        return name
    # Quote when necessary for spaces, reserved words, or mixed case.
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        escaped = name.replace('"', '""')
        return f'"{escaped}"'
    return name


def _serialize_column_list(columns: list[tuple[str, str]], limit: int = 8) -> str:
    names = [_quote_identifier(col) for col, _ in columns][:limit]
    return ", ".join(names) if names else "*"


def _normalize_text(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_ ]+", " ", text).lower()


def _is_numeric_type(col_type: str) -> bool:
    return any(t in col_type.lower() for t in ["int", "real", "float", "numeric", "decimal", "money"])


def _find_column_match(user_query: str, columns: list[tuple[str, str]], numeric_only: bool = False) -> str | None:
    q = _normalize_text(user_query)
    column_names = [col for col, typ in columns if not numeric_only or _is_numeric_type(typ)]
    for col in column_names:
        if col.lower() in q:
            return col

    tokens = set(q.split())
    for col in column_names:
        col_tokens = set(re.findall(r"\w+", col.lower()))
        if tokens & col_tokens:
            return col

    if numeric_only:
        return column_names[0] if column_names else None

    # prefer non-numeric columns for grouping
    non_numeric = [col for col, typ in columns if not _is_numeric_type(typ)]
    return non_numeric[0] if non_numeric else column_names[0] if column_names else None


def _find_group_column(user_query: str, columns: list[tuple[str, str]]) -> str | None:
    q = _normalize_text(user_query)
    group_phrases = re.findall(r"\bby ([a-z0-9_ ]+?)(?:$|,|;| and | or | for | with )", q)
    for phrase in group_phrases:
        phrase = phrase.strip()
        if phrase:
            group_col = _find_column_match(phrase, columns, numeric_only=False)
            if group_col:
                return group_col
    return _find_column_match(user_query, columns, numeric_only=False)


def _find_preferred_numeric_column(user_query: str, columns: list[tuple[str, str]], require_keyword_match: bool = False) -> str | None:
    q = _normalize_text(user_query)
    numeric_columns = [col for col, typ in columns if _is_numeric_type(typ)]
    if not numeric_columns:
        return None

    for col in numeric_columns:
        if col.lower() in q:
            return col

    preference_keywords = [
        "revenue",
        "profit",
        "amount",
        "sales",
        "quantity",
        "price",
        "total",
        "cost",
        "units",
        "income",
        "subtotal",
    ]
    keyword_match = next((col for col in numeric_columns if any(kw in col.lower() for kw in preference_keywords)), None)
    if keyword_match:
        return keyword_match

    if require_keyword_match:
        return None

    for col in numeric_columns:
        col_tokens = set(re.findall(r"\w+", col.lower()))
        if col_tokens & set(q.split()):
            return col

    return numeric_columns[0]


def _aggregation_for_query(user_query: str, columns: list[tuple[str, str]]) -> tuple[str, str | None]:
    q = _normalize_text(user_query)
    if re.search(r"\b(avg|average|mean)\b", q):
        agg_col = _find_preferred_numeric_column(q, columns)
        return ("AVG", agg_col)
    if re.search(r"\b(sum|total|revenue|profit|amount|sales|quantity|price|cost|income|units)\b", q):
        agg_col = _find_column_match(q, columns, numeric_only=True)
        if agg_col:
            return ("SUM", agg_col)
        agg_col = _find_preferred_numeric_column(q, columns, require_keyword_match=True)
        if agg_col:
            return ("SUM", agg_col)
        return ("COUNT", None)
    if re.search(r"\b(min|maximum|max|highest|lowest|min)\b", q):
        agg_col = _find_preferred_numeric_column(q, columns)
        if agg_col:
            if "max" in q or "highest" in q:
                return ("MAX", agg_col)
            return ("MIN", agg_col)
    if re.search(r"\b(count|how many|number of|frequency|distribution)\b", q):
        return ("COUNT", None)
    if re.search(r"\b(by|according to|per|between|group)\b", q):
        return ("COUNT", None)
    return (None, None)


def generate_sql_from_query(user_query: str, engine_override=None) -> str:
    q = user_query.strip()
    if not q:
        return "SELECT * FROM information_schema.tables LIMIT 100"

    schema_text = inspect_database_schema(engine_override)
    tables = _parse_schema_text(schema_text)
    if not tables:
        raise ValueError("Unable to inspect database schema for SQL generation.")

    if OPENAI_API_KEY:
        prompt = (
            "Generate a single PostgreSQL SELECT query for the following user request. "
            "Use only read-only SQL and do not include any explanatory text. "
            "If the user asks for grouping by a category without an explicit numeric operation, return COUNT(*) grouped by that category.\n\n"
            f"Database schema:\n{schema_text}\n\n"
            f"User request: {q}\n\n"
            "Return only SQL."
        )
        try:
            sql = ask_llm(prompt)
            return validate_sql(sql)
        except Exception:
            pass

    table = _best_table_for_query(q, tables)
    quoted_table = _quote_identifier(table)
    columns = tables[table]
    columns_sql = _serialize_column_list(columns)
    group_col = _find_group_column(q, columns)
    agg_fn, agg_col = _aggregation_for_query(q, columns)

    if agg_fn == "COUNT" and group_col:
        quoted_group = _quote_identifier(group_col)
        return (
            f"SELECT {quoted_group}, COUNT(*) AS total_count "
            f"FROM {quoted_table} GROUP BY {quoted_group} ORDER BY total_count DESC LIMIT 100"
        )
    if agg_fn == "COUNT":
        return f"SELECT COUNT(*) AS total_count FROM {quoted_table} LIMIT 100"
    if agg_fn in {"SUM", "AVG", "MIN", "MAX"} and agg_col:
        quoted_agg = _quote_identifier(agg_col)
        if group_col:
            quoted_group = _quote_identifier(group_col)
            alias = f"{agg_fn.lower()}_{agg_col.replace(' ', '_')}"
            return (
                f"SELECT {quoted_group}, {agg_fn}({quoted_agg}) AS {alias} "
                f"FROM {quoted_table} GROUP BY {quoted_group} ORDER BY {alias} DESC LIMIT 100"
            )
        return f"SELECT {agg_fn}({quoted_agg}) AS total_{agg_col.replace(' ', '_')} FROM {quoted_table} LIMIT 100"

    if re.search(r"\b(by|according to|per|group)\b", q.lower()) and group_col:
        quoted_group = _quote_identifier(group_col)
        return (
            f"SELECT {quoted_group}, COUNT(*) AS total_count "
            f"FROM {quoted_table} GROUP BY {quoted_group} ORDER BY total_count DESC LIMIT 100"
        )

    return f"SELECT {columns_sql} FROM {quoted_table} ORDER BY 1 LIMIT 100"

    if OPENAI_API_KEY:
        prompt = (
            "Generate a single PostgreSQL SELECT query for the following user request. "
            "Use only read-only SQL and do not include any explanatory text. "
            "If the request is about schema inspection, return a simple SELECT statement.\n\n"
            f"Database schema:\n{inspect_database_schema(engine_override)}\n\n"
            f"User request: {q}\n\n"
            "Return only SQL."
        )
        try:
            sql = ask_llm(prompt)
            return validate_sql(sql)
        except Exception:
            pass

    q = q.lower()
    if "sales" in q and "region" in q:
        return (
            "SELECT r.region_name, SUM(s.revenue) AS total_revenue, SUM(s.profit) AS total_profit\n"
            "FROM sales s\n"
            "JOIN regions r ON s.region_id = r.region_id\n"
            "GROUP BY r.region_name\n"
            "ORDER BY total_revenue DESC\n"
            "LIMIT 100"
        )

    if "sales" in q and "month" in q:
        return (
            "SELECT t.month, SUM(s.revenue) AS total_revenue, SUM(s.profit) AS total_profit\n"
            "FROM sales s\n"
            "JOIN time_periods t ON s.time_id = t.time_id\n"
            "GROUP BY t.month\n"
            "ORDER BY t.month\n"
            "LIMIT 100"
        )

    if "product" in q and ("sales" in q or "revenue" in q):
        return (
            "SELECT p.product_name, p.category, SUM(s.revenue) AS total_revenue, SUM(s.profit) AS total_profit\n"
            "FROM sales s\n"
            "JOIN products p ON s.product_id = p.product_id\n"
            "GROUP BY p.product_name, p.category\n"
            "ORDER BY total_revenue DESC\n"
            "LIMIT 100"
        )

    if "products" in q:
        return "SELECT product_id, product_name, category, unit_price FROM products ORDER BY product_name LIMIT 100"

    if "regions" in q or "region" in q:
        return "SELECT region_id, region_name, state, country FROM regions ORDER BY region_name LIMIT 100"

    if "time" in q or "year" in q or "month" in q:
        return "SELECT time_id, sale_date, month, quarter, year FROM time_periods ORDER BY sale_date LIMIT 100"

    return "SELECT sale_id, product_id, region_id, time_id, quantity, revenue, profit FROM sales ORDER BY sale_id LIMIT 100"


def run_query(sql: str) -> pd.DataFrame:
    return run_query_safe(sql)


def run_query_safe(sql: str, engine_override=None, max_rows: int = 1000, timeout_ms: int = 5000) -> pd.DataFrame:
    """Execute SQL safely inside a transaction with limits and timeouts.

    - Appends a LIMIT if the query does not contain one.
    - Attempts to set `statement_timeout` for Postgres-compatible engines.
    - Runs inside a transaction and returns a pandas DataFrame.
    """
    if not sql:
        raise ValueError("No SQL provided for execution.")

    eng = engine_override or engine

    normalized = sql.strip().lower()
    # Ensure there is a limit to avoid huge scans
    if "limit" not in normalized:
        sql_exec = f"{sql.strip()} LIMIT {max_rows}"
    else:
        sql_exec = sql.strip()

    with eng.connect() as conn:
        # Start a transaction block
        trans = conn.begin()
        try:
            # Try to set statement timeout for Postgres-like DBs
            try:
                conn.execute(text("SET LOCAL statement_timeout = :ms"), {"ms": timeout_ms})
            except OperationalError:
                # Not all DB backends support statement_timeout; ignore failures
                pass

            df = pd.read_sql(text(sql_exec), conn)
            trans.commit()
            return df
        except Exception:
            trans.rollback()
            raise


def create_chart(dataframe: pd.DataFrame):
    if dataframe.empty:
        return None

    numeric_columns = dataframe.select_dtypes(include="number").columns.tolist()
    if not numeric_columns:
        return None

    category_columns = dataframe.select_dtypes(exclude="number").columns.tolist()
    if category_columns:
        x_column = category_columns[0]
        y_column = numeric_columns[0]
        try:
            return px.bar(
                dataframe,
                x=x_column,
                y=y_column,
                title=f"{y_column.replace('_', ' ').title()} by {x_column.replace('_', ' ').title()}",
                labels={x_column: x_column.replace('_', ' ').title(), y_column: y_column.replace('_', ' ').title()},
            )
        except Exception:
            pass

    return px.line(
        dataframe,
        y=numeric_columns,
        title="Numeric values",
    )


def visualization_agent(dataframe: pd.DataFrame) -> Dict[str, Any]:
    """Choose appropriate charts based on the result set and return Plotly figures plus metadata."""
    if dataframe is None or dataframe.empty:
        return {"figures": [], "chart_types": []}

    numeric_columns = dataframe.select_dtypes(include="number").columns.tolist()
    category_columns = dataframe.select_dtypes(exclude="number").columns.tolist()
    datetime_columns = dataframe.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns.tolist()

    figures = []
    chart_types = []

    if category_columns and numeric_columns:
        fig = px.bar(
            dataframe,
            x=category_columns[0],
            y=numeric_columns[0],
            title=f"{numeric_columns[0].replace('_', ' ').title()} by {category_columns[0].replace('_', ' ').title()}",
            labels={
                category_columns[0]: category_columns[0].replace('_', ' ').title(),
                numeric_columns[0]: numeric_columns[0].replace('_', ' ').title(),
            },
        )
        figures.append(fig)
        chart_types.append("bar")

        if len(numeric_columns) > 1:
            fig2 = px.line(
                dataframe,
                x=category_columns[0],
                y=numeric_columns,
                title=f"{', '.join([c.replace('_', ' ').title() for c in numeric_columns])} by {category_columns[0].replace('_', ' ').title()}",
            )
            figures.append(fig2)
            chart_types.append("line")

    if datetime_columns and numeric_columns:
        fig = px.line(
            dataframe,
            x=datetime_columns[0],
            y=numeric_columns,
            title=f"{', '.join([c.replace('_', ' ').title() for c in numeric_columns])} over Time",
            labels={
                datetime_columns[0]: datetime_columns[0].replace('_', ' ').title(),
            },
        )
        figures.append(fig)
        chart_types.append("time_series")

    if not figures and len(numeric_columns) >= 2:
        fig = px.line(
            dataframe,
            y=numeric_columns,
            title="Numeric trends",
            labels={col: col.replace('_', ' ').title() for col in numeric_columns},
        )
        figures.append(fig)
        chart_types.append("line")

        if len(numeric_columns) == 2:
            fig2 = px.scatter(
                dataframe,
                x=numeric_columns[0],
                y=numeric_columns[1],
                title=f"{numeric_columns[1].replace('_', ' ').title()} vs {numeric_columns[0].replace('_', ' ').title()}",
                labels={
                    numeric_columns[0]: numeric_columns[0].replace('_', ' ').title(),
                    numeric_columns[1]: numeric_columns[1].replace('_', ' ').title(),
                },
            )
            figures.append(fig2)
            chart_types.append("scatter")

    if not figures and len(numeric_columns) == 1:
        fig = px.histogram(
            dataframe,
            x=numeric_columns[0],
            title=f"Distribution of {numeric_columns[0].replace('_', ' ').title()}",
            labels={numeric_columns[0]: numeric_columns[0].replace('_', ' ').title()},
            nbins=20,
        )
        figures.append(fig)
        chart_types.append("histogram")

        fig2 = px.box(
            dataframe,
            y=numeric_columns[0],
            title=f"Outliers for {numeric_columns[0].replace('_', ' ').title()}",
            labels={numeric_columns[0]: numeric_columns[0].replace('_', ' ').title()},
        )
        figures.append(fig2)
        chart_types.append("box")

    if figures:
        return {
            "figure": figures[0],
            "chart_type": chart_types[0],
            "figures": figures,
            "chart_types": chart_types,
        }

    return {"figure": None, "chart_type": None, "figures": [], "chart_types": []}


def insights_agent(dataframe: pd.DataFrame) -> str:
    """Generate executive insights using the LLM prompt file when available.

    Falls back to the existing `generate_insights` fallback logic.
    """
    if dataframe is None or dataframe.empty:
        return "No rows returned by the query."

    prompt_path = Path("prompts/insights_prompt.txt")
    sample = dataframe.head(5).to_dict(orient="records")
    cols = ", ".join(dataframe.columns.tolist())

    if OPENAI_API_KEY and prompt_path.exists():
        raw_template = prompt_path.read_text()
        prompt = raw_template.replace("{COLUMNS}", cols).replace("{SAMPLE_ROWS}", str(sample))
        try:
            insights = ask_llm(prompt)
            if insights:
                return insights.strip()
        except Exception:
            pass

    return generate_insights(dataframe)


def generate_insights(dataframe: pd.DataFrame) -> str:
    if dataframe.empty:
        return "No rows returned by the query."

    if OPENAI_API_KEY:
        sample = dataframe.head(5).to_dict(orient="records")
        prompt = (
            "You are a business analyst. Create a clear, concise summary of the query results in plain language. "
            "Use short bullet points and avoid SQL, technical details, or long paragraphs. "
            "Highlight the most important trends, high-level takeaways, and numeric observations.\n\n"
            f"Columns: {', '.join(dataframe.columns.tolist())}\n"
            f"Sample rows: {sample}\n\n"
            "Output the insights as a short list of readable bullet points."
        )
        try:
            summary = ask_llm(prompt)
            if summary:
                return summary.strip()
        except Exception:
            pass

    return _fallback_insights(dataframe)


def _fallback_insights(dataframe: pd.DataFrame) -> str:
    rows = len(dataframe)
    columns = list(dataframe.columns)
    lines = [
        "Insights:",
        f"- Rows returned: {rows}",
        f"- Columns: {', '.join(columns)}",
    ]

    numeric_columns = dataframe.select_dtypes(include="number").columns.tolist()
    for col in numeric_columns:
        values = dataframe[col].dropna()
        if values.empty:
            continue
        lines.append(
            f"- {col.replace('_', ' ').title()}: min {values.min():.2f}, max {values.max():.2f}, mean {values.mean():.2f}, median {values.median():.2f}"
        )
        lines.append(
            f"- {col.replace('_', ' ').title()} variance: {values.var():.2f}, std dev: {values.std():.2f}"
        )

    category_columns = dataframe.select_dtypes(exclude="number").columns.tolist()
    for col in category_columns:
        top = dataframe[col].mode()
        if not top.empty:
            lines.append(f"- Most common {col.replace('_', ' ').title()}: {top.iloc[0]}")

    if numeric_columns:
        max_col = max(numeric_columns, key=lambda c: dataframe[c].sum(skipna=True))
        lines.append(f"- Highest total is in {max_col.replace('_', ' ').title()}: {dataframe[max_col].sum(skipna=True):.2f}")

    return "\n".join(lines)
