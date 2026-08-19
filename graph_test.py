"""
graph_test.py

Integration tests for the full LangGraph workflow (run_workflow).
Uses an in-memory SQLite engine seeded with demo data.
No LLM required — exercises heuristic fallback paths.
"""

import pytest
import pandas as pd
from sqlalchemy import create_engine, text

from graph import run_workflow


@pytest.fixture(scope="module")
def demo_engine():
    """Seed a minimal in-memory SQLite DB for end-to-end workflow tests."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE products (
                product_id INTEGER PRIMARY KEY,
                product_name TEXT,
                category TEXT,
                unit_price REAL
            )
        """))
        conn.execute(text("""
            CREATE TABLE regions (
                region_id INTEGER PRIMARY KEY,
                region_name TEXT,
                state TEXT,
                country TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE sales (
                sale_id INTEGER PRIMARY KEY,
                product_id INTEGER,
                region_id INTEGER,
                quantity INTEGER,
                revenue REAL,
                profit REAL
            )
        """))
        conn.execute(text("""
            INSERT INTO products VALUES
              (1,'Laptop','Electronics',800),
              (2,'Mouse','Electronics',25),
              (3,'Desk','Furniture',300)
        """))
        conn.execute(text("""
            INSERT INTO regions VALUES
              (1,'Nagpur','Maharashtra','India'),
              (2,'Mumbai','Maharashtra','India'),
              (3,'Delhi','Delhi','India')
        """))
        conn.execute(text("""
            INSERT INTO sales VALUES
              (1,1,1,12,9600,2200),
              (2,2,2,120,3000,900),
              (3,3,3,18,5400,1600),
              (4,1,2,20,16000,4800),
              (5,2,1,250,6250,1800)
        """))
        conn.commit()
    return engine


class TestWorkflowStructure:
    def test_result_is_dict(self, demo_engine):
        result = run_workflow("show sales", engine_override=demo_engine)
        assert isinstance(result, dict)

    def test_result_has_required_keys(self, demo_engine):
        result = run_workflow("show sales", engine_override=demo_engine)
        expected_keys = ["sql", "dataframe", "plan", "insights", "figures", "elapsed_ms"]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_schema_populated(self, demo_engine):
        result = run_workflow("show products", engine_override=demo_engine)
        assert result.get("database_schema", "")  # non-empty

    def test_plan_has_steps(self, demo_engine):
        result = run_workflow("show total revenue by region", engine_override=demo_engine)
        plan = result.get("plan", {})
        assert isinstance(plan.get("steps", []), list)


class TestWorkflowSQLExecution:
    def test_sql_generated(self, demo_engine):
        result = run_workflow("show total revenue", engine_override=demo_engine)
        assert result.get("sql", "").strip().lower().startswith("select")

    def test_dataframe_returned(self, demo_engine):
        result = run_workflow("count sales", engine_override=demo_engine)
        df = result.get("dataframe")
        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    def test_rows_returned_positive(self, demo_engine):
        result = run_workflow("show all products", engine_override=demo_engine)
        assert result.get("rows_returned", 0) > 0

    def test_manual_sql_override(self, demo_engine):
        result = run_workflow(
            user_query="",
            manual_sql="SELECT product_name, unit_price FROM products",
            engine_override=demo_engine,
        )
        df = result.get("dataframe")
        assert df is not None
        assert "product_name" in df.columns

    def test_elapsed_ms_positive(self, demo_engine):
        result = run_workflow("show sales", engine_override=demo_engine)
        assert result.get("elapsed_ms", 0) > 0


class TestWorkflowVisualisation:
    def test_figures_list(self, demo_engine):
        result = run_workflow("show revenue by region chart", engine_override=demo_engine)
        assert isinstance(result.get("figures", []), list)

    def test_at_least_one_figure_for_data_query(self, demo_engine):
        result = run_workflow("compare revenue by region", engine_override=demo_engine)
        figures = result.get("figures", [])
        assert len(figures) >= 1, "Expected at least one chart"


class TestWorkflowGuardrail:
    def test_blocked_sql_sets_validation_error(self, demo_engine):
        result = run_workflow(
            user_query="",
            manual_sql="DROP TABLE sales",
            engine_override=demo_engine,
        )
        assert result.get("validation_error") is not None

    def test_blocked_sql_returns_no_dataframe(self, demo_engine):
        result = run_workflow(
            user_query="",
            manual_sql="DELETE FROM sales WHERE 1=1",
            engine_override=demo_engine,
        )
        df = result.get("dataframe")
        assert df is None or (hasattr(df, "empty") and df.empty)


class TestWorkflowInsights:
    def test_insights_non_empty(self, demo_engine):
        result = run_workflow("show total sales", engine_override=demo_engine)
        insights = result.get("insights", "")
        assert isinstance(insights, str)
        assert len(insights) > 10
