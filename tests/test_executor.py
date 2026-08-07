import pandas as pd
import agents
from agents import run_query
from sqlalchemy import create_engine, text


def test_run_query_with_sqlite(monkeypatch):
    # create an in-memory SQLite engine and populate data
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE test (id INTEGER PRIMARY KEY, value INTEGER)"))
        conn.execute(text("INSERT INTO test (value) VALUES (10)"))
        conn.execute(text("INSERT INTO test (value) VALUES (20)"))
        conn.execute(text("INSERT INTO test (value) VALUES (30)"))

    # patch the agents module engine to use the in-memory engine
    monkeypatch.setattr(agents, "engine", engine)

    df = run_query("SELECT * FROM test")
    assert isinstance(df, pd.DataFrame)
    assert df.shape[0] == 3
    assert "value" in df.columns
