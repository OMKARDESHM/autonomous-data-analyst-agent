from agents import generate_sql_from_query
from guardrails import validate_sql
from sqlalchemy import create_engine, text


def test_generate_sql_from_query_uses_schema(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name TEXT, revenue REAL)"))
        conn.execute(text("INSERT INTO customers (name, revenue) VALUES ('Acme', 100.0)"))
        conn.execute(text("INSERT INTO customers (name, revenue) VALUES ('Globex', 200.0)"))

    sql = generate_sql_from_query("Show customer revenue", engine_override=engine)
    assert isinstance(sql, str)
    assert sql.strip().lower().startswith("select")
    assert "customers" in sql.lower()
    validate_sql(sql)


def test_generate_sql_from_query_groups_by_category(engine_override=None):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE retail_sales_dataset (transaction_id INTEGER, gender TEXT, age INTEGER, revenue REAL)"))
        conn.execute(text("INSERT INTO retail_sales_dataset (transaction_id, gender, age, revenue) VALUES (1, 'Male', 32, 100.0)"))
        conn.execute(text("INSERT INTO retail_sales_dataset (transaction_id, gender, age, revenue) VALUES (2, 'Female', 28, 200.0)"))
        conn.execute(text("INSERT INTO retail_sales_dataset (transaction_id, gender, age, revenue) VALUES (3, 'Female', 35, 150.0)"))

    sql = generate_sql_from_query("Show sales by gender", engine_override=engine)
    assert isinstance(sql, str)
    assert "gender" in sql.lower()
    assert "group by" in sql.lower()
    validate_sql(sql)
