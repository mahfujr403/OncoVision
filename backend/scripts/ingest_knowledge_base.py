"""CLI script for ingesting curated knowledge base into OncoVision pgvector."""

import asyncio
import os
import sys

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Ensure .env is read from backend/.env if not in environment
from dotenv import load_dotenv

env_path = os.path.join(backend_dir, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

from app.rag.ingestion import run_cli

if __name__ == "__main__":
    asyncio.run(run_cli())
