"""
database/seed_sqlite.py

Standalone script to create (or re-create) the demo SQLite database at
database/demo.db using schema.sql + sample_data.sql.

Usage:
    python database/seed_sqlite.py
"""

import sys
from pathlib import Path

# Allow running from project root or from database/
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.reflection import create_demo_sqlite_engine, _DEMO_DB_PATH  # noqa: E402


def main() -> None:
    db_path = _DEMO_DB_PATH
    if db_path.exists():
        db_path.unlink()
        print(f"Removed existing demo DB: {db_path}")

    engine = create_demo_sqlite_engine(db_path)
    print(f"Demo SQLite DB created at: {db_path}")

    # Quick sanity check
    import pandas as pd
    from sqlalchemy import text
    with engine.connect() as conn:
        tables = pd.read_sql(
            text("SELECT name FROM sqlite_master WHERE type='table'"), conn
        )
    print("Tables:", tables["name"].tolist())
    print("Done. You can now upload demo.db in the Streamlit sidebar.")


if __name__ == "__main__":
    main()
