from agents import sql_specialist
from guardrails import validate_sql


def test_sql_specialist_generates_select():
    schema = (
        "Table: sales\n"
        "  - sale_id (integer)\n"
        "  - revenue (numeric)\n"
        "Table: regions\n"
        "  - region_id (integer)\n"
        "  - region_name (text)\n"
    )
    sql = sql_specialist("Show sales by region", schema)
    assert isinstance(sql, str)
    assert sql.strip().lower().startswith("select")
    # guardrails should accept the SQL (raises if not allowed)
    validate_sql(sql)
