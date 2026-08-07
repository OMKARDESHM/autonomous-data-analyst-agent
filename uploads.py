"""uploads.py

Helpers to accept uploaded files (CSV, Parquet, SQL dump, SQLite DB) and produce
an SQLAlchemy engine backed by a temporary SQLite database for safe querying.
"""
import os
import tempfile
import sqlite3
from typing import Optional
from sqlalchemy import create_engine
import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB limit by default


def _save_uploaded_file(uploaded_file, dest_path: str):
    # uploaded_file is a Streamlit UploadedFile with .getbuffer()
    with open(dest_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return dest_path


def create_engine_from_uploaded(uploaded_file, filename: str, max_bytes: int = MAX_UPLOAD_BYTES):
    """Accept an uploaded file and return a SQLAlchemy engine connected to a temp SQLite DB.

    Supported file types:
    - .db, .sqlite: returned engine pointing directly at the file
    - .csv: loaded into a temp SQLite table named after file (sanitized)
    - .parquet: loaded into a temp SQLite table
    - .sql: attempted to execute SQL statements into the temp SQLite

    Returns: (engine, temp_db_path)
    """
    name = filename.lower()
    # If UPLOADS_DIR is set, persist uploads there; otherwise use system temp dir
    uploads_dir = os.getenv("UPLOADS_DIR")
    if uploads_dir:
        Path(uploads_dir).mkdir(parents=True, exist_ok=True)
        tmpdir = uploads_dir
    else:
        tmpdir = tempfile.gettempdir()
    # Check size if possible
    try:
        size = len(uploaded_file.getbuffer())
        if size > max_bytes:
            raise ValueError(f"Uploaded file too large ({size} bytes)")
    except Exception:
        pass

    if name.endswith(('.db', '.sqlite')):
        dest = os.path.join(tmpdir, filename)
        _save_uploaded_file(uploaded_file, dest)
        engine = create_engine(f"sqlite:///{dest}")
        logger.info("Saved uploaded sqlite DB to %s", dest)
        return engine, dest

    # For CSV / Parquet / SQL, create a temporary SQLite DB
    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False, dir=tmpdir)
    tmp_db_path = tmp_db.name
    tmp_db.close()
    engine = create_engine(f"sqlite:///{tmp_db_path}")
    logger.info("Created temp sqlite DB at %s", tmp_db_path)

    if name.endswith('.csv'):
        dest = os.path.join(tmpdir, filename)
        _save_uploaded_file(uploaded_file, dest)
        df = pd.read_csv(dest)
        table_name = _sanitize_table_name(os.path.splitext(filename)[0])
        df.to_sql(table_name, engine, index=False, if_exists='replace')
        logger.info("Loaded CSV into table %s in %s", table_name, tmp_db_path)
        return engine, tmp_db_path

    if name.endswith('.parquet'):
        dest = os.path.join(tmpdir, filename)
        _save_uploaded_file(uploaded_file, dest)
        df = pd.read_parquet(dest)
        table_name = _sanitize_table_name(os.path.splitext(filename)[0])
        df.to_sql(table_name, engine, index=False, if_exists='replace')
        logger.info("Loaded Parquet into table %s in %s", table_name, tmp_db_path)
        return engine, tmp_db_path

    if name.endswith('.sql'):
        dest = os.path.join(tmpdir, filename)
        _save_uploaded_file(uploaded_file, dest)
        # Execute SQL statements into the sqlite DB
        with sqlite3.connect(tmp_db_path) as conn, open(dest, 'r', encoding='utf-8', errors='ignore') as f:
            sql = f.read()
            conn.executescript(sql)
        logger.info("Executed SQL dump into %s", tmp_db_path)
        return engine, tmp_db_path

    raise ValueError("Unsupported upload type; please upload .db, .sqlite, .csv, .parquet, or .sql")


def _sanitize_table_name(name: str) -> str:
    return ''.join(c if c.isalnum() or c == '_' else '_' for c in name)[:64]
