"""Entry point for Vercel, which looks for a FastAPI instance named `app` in main.py.

The application itself lives in backend/app; this file only makes that package importable.
Locally, run it from the backend folder as usual: uvicorn app.api:app
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app import api  # noqa: E402

app = api.app
