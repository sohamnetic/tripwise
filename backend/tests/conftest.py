import os

# Tests never touch paid APIs, even if backend/.env has real keys.
os.environ["DEMO_MODE"] = "true"
os.environ["DEMO_STEP_DELAY"] = "0"
os.environ["DATABASE_URL"] = "sqlite://"  # in-memory
os.environ["SERPAPI_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""
