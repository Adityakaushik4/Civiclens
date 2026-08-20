import os
import logging
from typing import Generator
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base

logger = logging.getLogger("civiclens.database")

Base = declarative_base()

RAW_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./civic_lens.db")
if RAW_DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = RAW_DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    DATABASE_URL = RAW_DATABASE_URL

DATABASE_POOL_SIZE = int(os.getenv("DATABASE_POOL_SIZE", "10"))
DATABASE_MAX_OVERFLOW = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))

# Configure Engine
connect_args = {}
engine_kwargs = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    connect_args["timeout"] = 15.0
    engine_kwargs["connect_args"] = connect_args
    if ":memory:" in DATABASE_URL:
        from sqlalchemy.pool import StaticPool
        engine_kwargs["poolclass"] = StaticPool
else:
    engine_kwargs["pool_size"] = DATABASE_POOL_SIZE
    engine_kwargs["max_overflow"] = DATABASE_MAX_OVERFLOW

import sys

if "pytest" in sys.modules and "civic_lens.db" in DATABASE_URL:
    raise RuntimeError("CRITICAL SAFETY GUARD: Pytest is attempting to connect to the development database 'civic_lens.db'. This is forbidden. Pytest must use test.db.")

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if DATABASE_URL.startswith("sqlite"):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA busy_timeout=15000;")
            cursor.close()
            dbapi_connection.commit()
        except Exception as e:
            logger.debug(f"Failed to set PRAGMA: {e}")


def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency providing a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_health() -> dict:
    """Checks database connectivity and returns health diagnostic."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "HEALTHY", "database_url_scheme": DATABASE_URL.split("://")[0]}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "UNHEALTHY", "error": str(e)}


def init_db() -> None:
    """Initializes database schema, extensions, and baseline development accounts."""
    try:
        if DATABASE_URL.startswith("postgresql"):
            try:
                with engine.connect() as conn:
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                    conn.commit()
            except Exception as ext_err:
                logger.info(f"Optional pgvector extension check skipped: {ext_err}")
        from app.database.models import Base, UserModel
        from app.auth.hash import hash_password
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema initialized successfully.")

        # Seed or refresh baseline accounts
        db = SessionLocal()
        try:
            baseline_users = [
                ("usr_admin01", "admin@civiclens.gov", "admin123", "System Administrator", "ADMIN"),
                ("usr_supervisor01", "supervisor@civiclens.gov", "supervisor123", "Municipal Supervisor", "SUPERVISOR"),
                ("usr_operator01", "operator@civiclens.gov", "operator123", "Field Operations Crew", "OPERATOR"),
                ("usr_citizen01", "citizen@civiclens.gov", "citizen123", "Citizen Reporter", "CITIZEN"),
            ]
            for uid, email, pwd, name, role in baseline_users:
                existing = db.query(UserModel).filter(UserModel.email == email).first()
                if not existing:
                    u = UserModel(
                        id=uid,
                        email=email,
                        password_hash=hash_password(pwd),
                        full_name=name,
                        role=role,
                        jurisdiction_id="GLOBAL",
                        is_active=True
                    )
                    db.add(u)
                else:
                    existing.password_hash = hash_password(pwd)
            db.commit()
            logger.info("Baseline development accounts seeded/refreshed successfully.")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Database init warning: {e}")

