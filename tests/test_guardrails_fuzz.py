import pytest
from guardrails import validate_sql


@pytest.mark.parametrize(
    "sql",
    [
        "D R O P TABLE users",
        "d r o p table users",
        "D\nR\nO\nP users",
        "/*inline*/ D R O P",
        "SeLeCt * FrOm (select 1) ; DROP TABLE t",
    ],
)
def test_guardrails_detects_obfuscated(sql):
    with pytest.raises(ValueError):
        validate_sql(sql)
