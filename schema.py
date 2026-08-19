"""
schema.py

GraphState definition shared across the entire LangGraph workflow.
Every node reads from and writes back into this typed dictionary.
"""

from typing import List, Dict, Any, Optional, TypedDict

import pandas as pd


class GraphState(TypedDict, total=False):
    # ── Input ─────────────────────────────────────────────────────────────────
    user_query: str
    manual_sql: Optional[str]
    engine_override: Any          # SQLAlchemy Engine, or None for default

    # ── Planner output ────────────────────────────────────────────────────────
    plan: Dict[str, Any]          # {sql_required, visualization_required, steps}
    planned_steps: List[str]

    # ── Schema ────────────────────────────────────────────────────────────────
    database_schema: str

    # ── SQL nodes ─────────────────────────────────────────────────────────────
    generated_sql: str
    sql: str                      # validated, final SQL
    validation_error: Optional[str]

    # ── Execution ─────────────────────────────────────────────────────────────
    dataframe: Optional[pd.DataFrame]
    dataframe_schema: Dict[str, str]
    rows_returned: int

    # ── Visualisation ─────────────────────────────────────────────────────────
    figure: Any                   # primary Plotly figure
    figures: List[Any]
    chart_type: str
    chart_types: List[str]

    # ── Insights ──────────────────────────────────────────────────────────────
    insights: str
    final_response: str

    # ── Metadata / control ────────────────────────────────────────────────────
    messages: List[Dict[str, str]]
    retry_count: int
    error: Optional[str]
    elapsed_ms: float
