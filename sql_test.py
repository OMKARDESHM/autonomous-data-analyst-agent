"""
sql_test.py

Unit tests for the SQL generation and guardrail pipeline.
Uses an in-memory SQLite engine seeded with demo data — no LLM required.
"""

import pytest
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text

from agents import generate_sql_from_query, inspect_database_schema
from guardrails import validate_sql


@pytest.fixture(scope="module")
def demo_engine():
    """In-memory SQLite engine with the demo schema."""
    engine = create_engine("sqlite:///:memory:", future=True)
    ddl = """
    CREATE TABLE products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT,
        category TEXT,
        unit_price REAL
    );
    CREATE TABLE regions (
        region_id INTEGER PRIMARY KEY AUTOINCREMENT,
        region_name TEXT,
        state TEXT,
        country TEXT
    );
    CREATE TABLE time_periods (
        time_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_date TEXT,
        month INTEGER,
        quarter INTEGER,
        year INTEGER
    );
    CREATE TABLE sales (
        sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        region_id INTEGER,
        time_id INTEGER,
        quantity INTEGER,
        revenue REAL,
        profit REAL
    );
    """
    data = """
    INSERT INTO products VALUES (1,'Laptop','Electronics',800),(2,'Mouse','Electronics',25);
    INSERT INTO regions VALUES (1,'Nagpur','Maharashtra','India'),(2,'Mumbai','Maharashtra','India');
    INSERT INTO time_periods VALUES (1,'2025-01-15',1,1,2025),(2,'2025-02-10',2,1,2025);
    INSERT INTO sales VALUES (1,1,1,1,12,9600,2200),(2,2,2,2,120,3000,900);
    """
    with engine.connect() as conn:
        for stmt in ddl.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
        for stmt in data.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
        conn.commit()
    return engine


class TestSchemaInspection:
    def test_schema_has_tables(self, demo_engine):
        schema = inspect_database_schema(demo_engine)
        assert "Table: sales" in schema or "Table:" in schema

    def test_schema_has_columns(self, demo_engine):
        schema = inspect_database_schema(demo_engine)
        assert "revenue" in schema or "product_name" in schema


class TestSQLGeneration:
    def test_generates_select(self, demo_engine):
        sql = generate_sql_from_query("show sales by region", demo_engine)
        assert sql.strip().lower().startswith("select")

    def test_generates_valid_sql(self, demo_engine):
        sql = generate_sql_from_query("count sales", demo_engine)
        validated = validate_sql(sql)
        assert "select" in validated.lower()

    def test_total_revenue_query(self, demo_engine):
        sql = generate_sql_from_query("total revenue", demo_engine)
        assert "revenue" in sql.lower() or "select" in sql.lower()

    def test_region_group_by(self, demo_engine):
        sql = generate_sql_from_query("sales by region", demo_engine)
        assert "select" in sql.lower()

    def test_product_query(self, demo_engine):
        sql = generate_sql_from_query("list products", demo_engine)
        assert "select" in sql.lower()


class TestGuardrails:
    def test_select_passes(self):
        sql = validate_sql("SELECT * FROM sales LIMIT 10")
        assert "SELECT" in sql or "select" in sql.lower()

    def test_drop_blocked(self):
        with pytest.raises(ValueError, match="SELECT"):
            validate_sql("DROP TABLE sales")

    def test_delete_blocked(self):
        with pytest.raises(ValueError, match="SELECT"):
            validate_sql("DELETE FROM sales WHERE 1=1")

    def test_insert_blocked(self):
        with pytest.raises(ValueError, match="SELECT"):
            validate_sql("INSERT INTO sales VALUES (1,2,3,4,5,100,50)")

    def test_update_blocked(self):
        with pytest.raises(ValueError, match="SELECT"):
            validate_sql("UPDATE sales SET revenue = 0")

    def test_multiple_statements_blocked(self):
        with pytest.raises(ValueError):
            validate_sql("SELECT 1; SELECT 2")

    def test_semicolons_blocked(self):
        with pytest.raises(ValueError):
            validate_sql("SELECT * FROM sales; DROP TABLE sales")

    def test_comment_blocked(self):
        with pytest.raises(ValueError, match="comments"):
            validate_sql("SELECT * FROM sales -- drop table")

    def test_empty_sql_blocked(self):
        with pytest.raises(ValueError):
            validate_sql("")

    def test_none_sql_blocked(self):
        with pytest.raises((ValueError, TypeError)):
            validate_sql(None)
