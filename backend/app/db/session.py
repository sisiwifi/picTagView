from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text

from app.core.config import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _migrate_db()


def _migrate_db() -> None:
    """Add new columns to existing tables if they don't exist yet."""
    with engine.connect() as conn:
        for column, col_type in [("media_path", "TEXT"), ("date_group", "TEXT")]:
            try:
                conn.execute(
                    text(f"ALTER TABLE imageasset ADD COLUMN {column} {col_type}")
                )
                conn.commit()
            except Exception:
                # Column already exists — safe to ignore
                pass


def get_session() -> Session:
    return Session(engine)
