"""
config.py

Central configuration for the Autonomous Data Analyst Agent.
Supports NVIDIA NIM (primary) and OpenAI (fallback) via LangChain.
"""

from dotenv import load_dotenv
import os
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

logger = logging.getLogger(__name__)

# ── LLM Configuration ─────────────────────────────────────────────────────────
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "meta/llama-3.1-8b-instruct")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# ── Database Configuration ────────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/salesdb",
)


def get_llm():
    """Return a LangChain chat model.

    Priority:
    1. ChatNVIDIA  — when NVIDIA_API_KEY is set
    2. ChatOpenAI  — when OPENAI_API_KEY is set
    3. None        — heuristic fallbacks will be used
    """
    if NVIDIA_API_KEY:
        try:
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            llm = ChatNVIDIA(
                model=MODEL_NAME,
                api_key=NVIDIA_API_KEY,
                temperature=0,
                max_tokens=1024,
            )
            logger.info("Using NVIDIA NIM LLM: %s", MODEL_NAME)
            return llm
        except Exception as exc:
            logger.warning("Failed to initialise ChatNVIDIA: %s", exc)

    if OPENAI_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model=OPENAI_MODEL,
                api_key=OPENAI_API_KEY,
                temperature=0,
                max_tokens=1024,
            )
            logger.info("Using OpenAI LLM: %s", OPENAI_MODEL)
            return llm
        except Exception as exc:
            logger.warning("Failed to initialise ChatOpenAI: %s", exc)

    logger.info("No LLM API key set — heuristic fallbacks will be used.")
    return None


# ── Database Engine ───────────────────────────────────────────────────────────
try:
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        future=True,
    )
except Exception as _db_exc:  # pragma: no cover
    logger.warning("Could not create DB engine: %s", _db_exc)
    engine = None  # type: ignore[assignment]

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
) if engine else None
