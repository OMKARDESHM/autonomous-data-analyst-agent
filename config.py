"""
config.py

Central configuration for the Autonomous Data Analyst Agent.
"""

from dotenv import load_dotenv

import os

from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker

from langchain_nvidia_ai_endpoints import ChatNVIDIA


load_dotenv()


NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

DATABASE_URL = os.getenv("DATABASE_URL")


if NVIDIA_API_KEY is None:
    raise RuntimeError("NVIDIA_API_KEY not found in .env")

if DATABASE_URL is None:
    raise RuntimeError("DATABASE_URL not found in .env")


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
)


llm = ChatNVIDIA(
    model="nvidia/llama-3.1-nemotron-70b-instruct",
    api_key=NVIDIA_API_KEY,
    temperature=0,
)