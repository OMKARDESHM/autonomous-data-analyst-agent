import pytest
from guardrails import validate_sql


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE users;",
        "DELETE FROM sales WHERE 1=1;",
        "SELECT * FROM a; SELECT * FROM b;",
        "-- comment\nSELECT * FROM sales",
        "/* block comment */ SELECT * FROM sales",
        "INSERT INTO sales (id) VALUES (1)",
        "UPDATE sales SET revenue = 0",
    ],
)
def test_guardrails_rejects_destructive_or_multiple(sql):
    with pytest.raises(ValueError):
        validate_sql(sql)


def test_guardrails_accepts_simple_select():
    sql = "SELECT id, revenue FROM sales WHERE revenue > 100"
    assert validate_sql(sql) == sql
