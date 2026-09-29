import os
import tempfile
from pathlib import Path

# Tests never touch paid APIs, even if backend/.env has real keys.
os.environ["DEMO_MODE"] = "true"
os.environ["DEMO_STEP_DELAY"] = "0"
os.environ["SERPAPI_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["GEOAPIFY_KEY"] = ""
os.environ.pop("VERCEL", None)
# A throwaway database file (an in-memory SQLite DB would be empty for every new connection).
_db = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db.as_posix()}"
