"""
executor_test.py

Unit tests for the SQL executor (run_query_safe).
Uses an in-memory SQLite engine — no live database required.
"""

import pytest
import pandas as pd
from sqlalchemy import create_engine, text

from agents import run_query_safe
from guardrails import validate_sql


@pytest.fixture(scope="module")
def demo_engine():
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE sales (
                sale_id INTEGER PRIMARY KEY,
                region TEXT,
                revenue REAL,
                profit REAL
            )
        """))
        conn.execute(text("""
            INSERT INTO sales VALUES
              (1,'North',10000,3000),
              (2,'South',8000,2000),
              (3,'East',12000,4000),
              (4,'West',9500,2800)
        """))
        conn.commit()
    return engine


class TestRunQuerySafe:
    def test_basic_select(self, demo_engine):
        df = run_query_safe("SELECT * FROM sales", engine_override=demo_engine)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 4

    def test_returns_dataframe(self, demo_engine):
        df = run_query_safe("SELECT region, revenue FROM sales", engine_override=demo_engine)
        assert "region" in df.columns
        assert "revenue" in df.columns

    def test_where_clause(self, demo_engine):
        df = run_query_safe(
            "SELECT * FROM sales WHERE region = 'North'",
            engine_override=demo_engine,
        )
        assert len(df) == 1
        assert df.iloc[0]["revenue"] == 10000

    def test_aggregate_sum(self, demo_engine):
        df = run_query_safe(
            "SELECT SUM(revenue) AS total_revenue FROM sales",
            engine_override=demo_engine,
        )
        assert df.iloc[0]["total_revenue"] == pytest.approx(39500)

    def test_group_by(self, demo_engine):
        df = run_query_safe(
            "SELECT region, SUM(revenue) AS total_revenue FROM sales GROUP BY region",
            engine_override=demo_engine,
        )
        assert len(df) == 4

    def test_order_by(self, demo_engine):
        df = run_query_safe(
            "SELECT region, revenue FROM sales ORDER BY revenue DESC",
            engine_override=demo_engine,
        )
        assert df.iloc[0]["region"] == "East"

    def test_limit_applied(self, demo_engine):
        df = run_query_safe(
            "SELECT * FROM sales LIMIT 2",
            engine_override=demo_engine,
        )
        assert len(df) == 2

    def test_auto_limit_applied(self, demo_engine):
        # No LIMIT in query — executor should auto-append LIMIT 1000
        df = run_query_safe(
            "SELECT * FROM sales",
            engine_override=demo_engine,
            max_rows=2,
        )
        # Result should be limited to 2
        assert len(df) <= 2

    def test_empty_result(self, demo_engine):
        df = run_query_safe(
            "SELECT * FROM sales WHERE revenue > 999999",
            engine_override=demo_engine,
        )
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_empty_sql_raises(self, demo_engine):
        with pytest.raises(ValueError, match="No SQL"):
            run_query_safe("", engine_override=demo_engine)

    def test_invalid_sql_raises(self, demo_engine):
        with pytest.raises(Exception):
            run_query_safe("SELECT * FROM nonexistent_table_xyz", engine_override=demo_engine)
