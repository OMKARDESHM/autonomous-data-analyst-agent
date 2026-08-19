"""
state.py

Factory for the initial GraphState passed into the LangGraph workflow.
"""

from typing import Optional
from schema import GraphState


def initial_state(
    user_query: str,
    manual_sql: Optional[str] = None,
    engine_override=None,
) -> GraphState:
    """Return a fresh GraphState ready for the workflow to process."""
    return GraphState(
        user_query=user_query,
        manual_sql=manual_sql,
        engine_override=engine_override,
        plan={},
        planned_steps=[],
        database_schema="",
        generated_sql="",
        sql="",
        validation_error=None,
        dataframe=None,
        dataframe_schema={},
        rows_returned=0,
        figure=None,
        figures=[],
        chart_type="",
        chart_types=[],
        insights="",
        final_response="",
        messages=[],
        retry_count=0,
        error=None,
        elapsed_ms=0.0,
    )
