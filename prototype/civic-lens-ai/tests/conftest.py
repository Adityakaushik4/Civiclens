import os
import sys
import pytest

# CRITICAL: Isolate tests from the development database
# Set the environment variable BEFORE any app modules are imported
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

# Safety: If app.database.connection was already loaded by something else, reload it
if "app.database.connection" in sys.modules:
    import importlib
    importlib.reload(sys.modules["app.database.connection"])

# Now we can safely import app modules
from app.database.connection import init_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """
    Automatically creates the test database schema before any tests run,
    and removes the test.db file after all tests finish.
    """
    # Ensure any stale test DB is removed before starting
    if os.path.exists("test.db"):
        try:
            os.remove("test.db")
        except OSError:
            pass

    # Initialize schema in test.db
    init_db()
    
    yield
    
    # Cleanup after all tests
    try:
        from sqlalchemy.orm import close_all_sessions
        from app.database.connection import engine
        close_all_sessions()
        engine.dispose()
    except Exception:
        pass

    if os.path.exists("test.db"):
        try:
            os.remove("test.db")
        except OSError:
            pass
