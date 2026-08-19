"""
graph.py

LangGraph StateGraph workflow for the Autonomous Data Analyst Agent.

Pipeline nodes (in order):
  schema_node → planner_node → sql_node → guardrail_node
  → executor_node → visualization_node → insights_node
"""

import logging
import time
from typing import Optional

from langgraph.graph import StateGraph, END

from schema import GraphState
from state import initial_state
from agents import (
    schema_agent,
    planner_agent,
    sql_specialist,
    generate_sql_from_query,
    run_query_safe,
    visualization_agent,
    insights_agent,
)
from guardrails import validate_sql

logger = logging.getLogger(__name__)


# ── Node Implementations ──────────────────────────────────────────────────────

def schema_node(state: GraphState) -> GraphState:
    """Inspect the connected database and populate database_schema."""
    logger.info("[schema_node] Inspecting schema")
    schema = schema_agent(state.get("engine_override"))
    return {**state, "database_schema": schema}


def planner_node(state: GraphState) -> GraphState:
    """Decide the execution plan (sql_required, visualization_required, steps)."""
    logger.info("[planner_node] Planning")
    plan = planner_agent(state["user_query"], state.get("database_schema"))
    return {
        **state,
        "plan": plan,
        "planned_steps": plan.get("steps", []),
    }


def sql_node(state: GraphState) -> GraphState:
    """Generate a SQL query from the user request and schema."""
    manual = state.get("manual_sql") or ""
    if manual.strip():
        logger.info("[sql_node] Using manual SQL")
        return {**state, "generated_sql": manual.strip()}

    plan = state.get("plan", {})
    if not plan.get("sql_required", True):
        logger.info("[sql_node] SQL not required by planner")
        return {**state, "generated_sql": ""}

    logger.info("[sql_node] Generating SQL via specialist")
    sql = sql_specialist(
        state["user_query"],
        state.get("database_schema", ""),
        engine_override=state.get("engine_override"),
    )
    return {**state, "generated_sql": sql}


def guardrail_node(state: GraphState) -> GraphState:
    """Validate the generated SQL before execution."""
    sql = state.get("generated_sql", "").strip()
    if not sql:
        return {**state, "sql": "", "validation_error": None}

    try:
        clean = validate_sql(sql)
        logger.info("[guardrail_node] SQL validated ✓")
        return {**state, "sql": clean, "validation_error": None}
    except ValueError as exc:
        logger.warning("[guardrail_node] SQL blocked: %s", exc)
        return {**state, "sql": "", "validation_error": str(exc)}


def executor_node(state: GraphState) -> GraphState:
    """Execute the validated SQL and load results into a DataFrame."""
    sql = state.get("sql", "")
    if not sql:
        return {**state, "dataframe": None, "rows_returned": 0}

    logger.info("[executor_node] Executing SQL")
    df = run_query_safe(sql, engine_override=state.get("engine_override"))
    schema_map = {col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)}
    return {
        **state,
        "dataframe": df,
        "dataframe_schema": schema_map,
        "rows_returned": len(df),
    }


def visualization_node(state: GraphState) -> GraphState:
    """Create Plotly figures from the query DataFrame."""
    df = state.get("dataframe")
    plan = state.get("plan", {})
    if df is None or df.empty or not plan.get("visualization_required", True):
        return {**state, "figure": None, "figures": [], "chart_type": "", "chart_types": []}

    logger.info("[visualization_node] Building charts")
    viz = visualization_agent(df)
    return {
        **state,
        "figure": viz.get("figure"),
        "figures": viz.get("figures", []),
        "chart_type": viz.get("chart_type", ""),
        "chart_types": viz.get("chart_types", []),
    }


def insights_node(state: GraphState) -> GraphState:
    """Generate an executive insight summary from the result DataFrame."""
    df = state.get("dataframe")
    if df is None or df.empty:
        msg = state.get("validation_error") or "No SQL execution required for this request."
        return {**state, "insights": msg, "final_response": msg}

    logger.info("[insights_node] Generating insights")
    insights = insights_agent(df)
    return {**state, "insights": insights, "final_response": insights}


# ── Conditional Routing ───────────────────────────────────────────────────────

def _route_after_guardrail(state: GraphState) -> str:
    """Route to executor if SQL is clean; skip to visualization if blocked."""
    if state.get("validation_error"):
        return "visualization_node"
    sql = state.get("sql", "").strip()
    return "executor_node" if sql else "visualization_node"


# ── Graph Assembly ────────────────────────────────────────────────────────────

def _build_graph() -> StateGraph:
    graph = StateGraph(GraphState)

    graph.add_node("schema_node", schema_node)
    graph.add_node("planner_node", planner_node)
    graph.add_node("sql_node", sql_node)
    graph.add_node("guardrail_node", guardrail_node)
    graph.add_node("executor_node", executor_node)
    graph.add_node("visualization_node", visualization_node)
    graph.add_node("insights_node", insights_node)

    graph.set_entry_point("schema_node")

    graph.add_edge("schema_node", "planner_node")
    graph.add_edge("planner_node", "sql_node")
    graph.add_edge("sql_node", "guardrail_node")
    graph.add_conditional_edges(
        "guardrail_node",
        _route_after_guardrail,
        {
            "executor_node": "executor_node",
            "visualization_node": "visualization_node",
        },
    )
    graph.add_edge("executor_node", "visualization_node")
    graph.add_edge("visualization_node", "insights_node")
    graph.add_edge("insights_node", END)

    return graph


_compiled_graph = _build_graph().compile()


# ── Public API ────────────────────────────────────────────────────────────────

def run_workflow(
    user_query: str,
    manual_sql: Optional[str] = None,
    engine_override=None,
) -> dict:
    """Run the full multi-agent pipeline and return a result dict.

    Compatible with the original flat-dict API consumed by app.py.
    """
    state = initial_state(
        user_query=user_query,
        manual_sql=manual_sql,
        engine_override=engine_override,
    )

    t0 = time.perf_counter()
    result: GraphState = _compiled_graph.invoke(state)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    return {
        "database_schema": result.get("database_schema", ""),
        "plan": result.get("plan", {}),
        "planned_steps": result.get("planned_steps", []),
        "sql": result.get("sql", ""),
        "validation_error": result.get("validation_error"),
        "dataframe": result.get("dataframe"),
        "rows_returned": result.get("rows_returned", 0),
        "figure": result.get("figure"),
        "figures": result.get("figures", []),
        "chart_type": result.get("chart_type", ""),
        "chart_types": result.get("chart_types", []),
        "insights": result.get("insights", ""),
        "final_response": result.get("final_response", ""),
        "elapsed_ms": elapsed_ms,
    }
