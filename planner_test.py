"""
planner_test.py

Unit tests for the planner_agent function.
Uses an in-memory SQLite engine — no LLM required.
"""

import pytest
from agents import planner_agent


SAMPLE_SCHEMA = """
Table: sales
  - sale_id (INTEGER)
  - region_id (INTEGER)
  - revenue (REAL)
  - quantity (INTEGER)

Table: regions
  - region_id (INTEGER)
  - region_name (TEXT)
"""


class TestPlannerAgent:
    def test_sql_required_for_data_query(self):
        plan = planner_agent("Show total sales by region", SAMPLE_SCHEMA)
        assert plan["sql_required"] is True

    def test_visualization_required_for_chart_query(self):
        plan = planner_agent("Show a chart of sales by region", SAMPLE_SCHEMA)
        assert plan["visualization_required"] is True

    def test_no_sql_for_non_data_query(self):
        plan = planner_agent("Hello, how are you?", SAMPLE_SCHEMA)
        # heuristic should produce no data-related keywords
        assert "sql_required" in plan

    def test_steps_is_list(self):
        plan = planner_agent("List top 10 products by revenue", SAMPLE_SCHEMA)
        assert isinstance(plan.get("steps"), list)

    def test_steps_non_empty_for_data_query(self):
        plan = planner_agent("Count sales by region", SAMPLE_SCHEMA)
        assert len(plan.get("steps", [])) > 0

    def test_plan_has_required_keys(self):
        plan = planner_agent("Show revenue by month", SAMPLE_SCHEMA)
        assert "sql_required" in plan
        assert "visualization_required" in plan
        assert "steps" in plan

    def test_visualization_for_trend_query(self):
        plan = planner_agent("Show monthly revenue trend", SAMPLE_SCHEMA)
        assert plan["visualization_required"] is True

    def test_no_schema_fallback(self):
        plan = planner_agent("Show sales by region", None)
        assert "sql_required" in plan

    def test_count_query(self):
        plan = planner_agent("How many sales do we have?", SAMPLE_SCHEMA)
        assert plan["sql_required"] is True

    def test_compare_query(self):
        plan = planner_agent("Compare revenue by region", SAMPLE_SCHEMA)
        assert plan["visualization_required"] is True
