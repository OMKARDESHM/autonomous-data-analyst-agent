"""
graph.py

Simplified workflow for the Autonomous Data Analyst Agent.
"""

from typing import Optional

from agents import (
    inspect_database_schema,
    planner_agent,
    sql_specialist,
    generate_sql_from_query,
    run_query_safe,
    visualization_agent,
    insights_agent,
)
from guardrails import validate_sql


def run_workflow(user_query: str, manual_sql: Optional[str] = None, engine_override=None) -> dict:
    """Run a LangGraph-like multi-agent pipeline:

    1. Inspect schema
    2. Planner decides the execution plan
    3. SQL Specialist generates SQL (unless manual SQL provided)
    4. Guardrails validate SQL
    5. Executor runs the query
    6. Visualization agent creates a chart if requested
    7. Insight agent summarizes results
    """
    schema = inspect_database_schema(engine_override)

    # Planner
    plan = planner_agent(user_query, schema)

    # SQL generation (manual SQL takes precedence)
    if manual_sql and manual_sql.strip():
        sql = validate_sql(manual_sql.strip())
    elif plan.get("sql_required", True):
        sql = sql_specialist(user_query, schema, engine_override=engine_override)
    else:
        sql = None

    dataframe = None
    figure = None
    chart_type = None
    insights = ""

    if sql:
        sql = validate_sql(sql)
        dataframe = run_query_safe(sql, engine_override=engine_override)
        if plan.get("visualization_required", True):
            viz = visualization_agent(dataframe)
            figure = viz.get("figure")
            chart_type = viz.get("chart_type")
            figures = viz.get("figures", [])
            chart_types = viz.get("chart_types", [])
        insights = insights_agent(dataframe)
    else:
        insights = "No SQL execution required for this request."

    return {
        "database_schema": schema,
        "plan": plan,
        "sql": sql,
        "dataframe": dataframe,
        "figure": figure,
        "chart_type": chart_type,
        "figures": figures,
        "chart_types": chart_types,
        "insights": insights,
    }
