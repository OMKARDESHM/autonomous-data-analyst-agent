"""
database/reflection.py

SQLAlchemy schema reflection utilities and demo SQLite engine factory.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# ── Schema Reflection ─────────────────────────────────────────────────────────

def reflect_schema(engine: Engine, sample_rows: int = 3) -> str:
    """Inspect *engine* and return a human-readable schema description.

    For each table the output lists column names with their SQL types and
    (optionally) a few sample rows to give the LLM context about real values.
    """
    lines: list[str] = []
    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        if not table_names:
            return "No tables found in the database."

        for table in table_names:
            lines.append(f"Table: {table}")
            for col in inspector.get_columns(table):
                lines.append(f"  - {col['name']} ({col['type']})")

            if sample_rows > 0:
                try:
                    quoted = _quote(table)
                    with engine.connect() as conn:
                        df = pd.read_sql(
                            text(f"SELECT * FROM {quoted} LIMIT {sample_rows}"),
                            conn,
                        )
                    if not df.empty:
                        lines.append("  Sample rows:")
                        for row in df.to_dict(orient="records"):
                            lines.append(f"    {row}")
                except Exception as exc:
                    logger.debug("Could not fetch sample rows for %s: %s", table, exc)

    except Exception as exc:
        logger.warning("Schema reflection failed: %s", exc)
        return "Schema could not be inspected."

    return "\n".join(lines) if lines else "No schema available."


def _quote(name: str) -> str:
    """Double-quote an identifier that may contain spaces or reserved words."""
    import re
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        return name
    return '"' + name.replace('"', '""') + '"'


# ── Demo SQLite Engine ────────────────────────────────────────────────────────

_DEMO_DB_PATH = Path(__file__).parent / "demo.db"
_SCHEMA_SQL = Path(__file__).parent / "schema.sql"
_DATA_SQL = Path(__file__).parent / "sample_data.sql"


def create_demo_sqlite_engine(db_path: Optional[Path] = None) -> Engine:
    """Return a SQLAlchemy engine backed by the demo SQLite database.

    If *db_path* does not exist yet it is seeded from schema.sql + sample_data.sql.
    """
    path = db_path or _DEMO_DB_PATH
    if not path.exists():
        _seed_demo_db(path)
    engine = create_engine(f"sqlite:///{path}", future=True)
    logger.info("Demo SQLite engine ready at %s", path)
    return engine


def _seed_demo_db(path: Path) -> None:
    """Create and populate the demo SQLite database from SQL files."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        for sql_file in (_SCHEMA_SQL, _DATA_SQL):
            if sql_file.exists():
                sql = sql_file.read_text(encoding="utf-8")
                # SQLite does not support SERIAL; replace with AUTOINCREMENT syntax
                sql = sql.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
                sql = sql.replace("DECIMAL(10,2)", "REAL")
                sql = sql.replace("DECIMAL(12,2)", "REAL")
                sql = sql.replace("VARCHAR(100)", "TEXT")
                # Remove DROP IF EXISTS for SQLite compat (already handled by IF NOT EXISTS)
                conn.executescript(sql)
        conn.commit()
        logger.info("Demo DB seeded at %s", path)
    finally:
        conn.close()
