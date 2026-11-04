"""Top-level backend runner.

Launches the FastAPI server on 127.0.0.1:8000.
Usage:
  python backend/main.py
"""
import sys
from pathlib import Path
import uvicorn

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app
from app.db import init_db

if __name__ == "__main__":
    init_db()
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)

