"""
guardrails.py

Simple SQL validation for read-only SELECT statements.
"""

import re
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Token
from sqlparse.tokens import DML, Keyword


FORBIDDEN_WORDS = {"insert", "update", "delete", "drop", "alter", "truncate", "create", "replace", "grant", "revoke", "shutdown", "merge"}


def _first_dml(statement) -> str:
    for token in statement.tokens:
        if token.ttype is DML:
            return token.value.lower()
        # nested tokens
        if hasattr(token, "tokens"):
            for sub in token.tokens:
                if sub.ttype is DML:
                    return sub.value.lower()
    return ""


def validate_sql(sql: str) -> str:
    if sql is None:
        raise ValueError("No SQL statement provided.")

    cleaned = sql.strip()
    if not cleaned:
        raise ValueError("SQL statement is empty.")

    # strip comments using sqlparse
    formatted = sqlparse.format(cleaned, strip_comments=True)
    statements = sqlparse.parse(formatted)
    if len(statements) != 1:
        raise ValueError("Only a single SQL statement is allowed.")

    stmt = statements[0]
    first = _first_dml(stmt)
    if not first:
        # no DML found: reject
        raise ValueError("Only SELECT statements are allowed.")
    if first != "select":
        raise ValueError("Only SELECT statements are allowed.")

    # Lowercase text for searches
    norm = formatted.lower()

    # Disallow common destructive keywords anywhere
    for word in FORBIDDEN_WORDS:
        if re.search(r"\b" + re.escape(word) + r"\b", norm):
            raise ValueError("Only read-only SELECT queries are allowed.")

    # Detect obfuscated letter-separated attempts like 'D R O P' or 'd r o p'
    for word in FORBIDDEN_WORDS:
        spaced = r"\b" + r"\s*".join(list(word)) + r"\b"
        if re.search(spaced, formatted, flags=re.IGNORECASE):
            raise ValueError("Only read-only SELECT queries are allowed.")

    # Disallow explicit semicolons that end statements
    if ";" in cleaned:
        raise ValueError("Semicolons are not allowed; only a single SELECT statement is permitted.")

    # Disallow comments markers (already stripped, but check original)
    if "--" in cleaned or "/*" in cleaned:
        raise ValueError("SQL comments are not allowed in user-provided queries.")

    return cleaned
