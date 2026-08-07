from agents import generate_sql_from_query
from guardrails import validate_sql
from sqlalchemy import create_engine, text


def test_generate_sql_quotes_identifiers_with_spaces():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE "retail_sales_dataset" ("Transaction ID" INTEGER, "Age" INTEGER)'))
        conn.execute(text('INSERT INTO "retail_sales_dataset" ("Transaction ID", "Age") VALUES (1, 30)'))

    sql = generate_sql_from_query("Show total age by transaction id", engine_override=engine)
    assert "\"Transaction ID\"" in sql or "COUNT" in sql.lower()
    validate_sql(sql)
