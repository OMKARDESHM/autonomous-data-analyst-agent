"""
config.py

Central configuration for the Autonomous Data Analyst Agent.
"""

from dotenv import load_dotenv
import os

import openai
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/salesdb",
)

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)
