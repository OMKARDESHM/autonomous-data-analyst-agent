"""
schema.py

State definitions shared across the workflow.
"""

from typing import List, Dict, Any, Optional, TypedDict

import pandas as pd


class GraphState(TypedDict):
    user_query: str
    planned_steps: List[str]
    database_schema: str
    generated_sql: str
    validation_error: Optional[str]
    dataframe: Optional[pd.DataFrame]
    dataframe_schema: Dict[str, str]
    plotly_code: str
    figure: Any
    final_response: str
    messages: List[Dict[str, str]]
    retry_count: int
    error: Optional[str]
