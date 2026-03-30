import json

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
        for column, col_type in [
            ("media_path", "TEXT"),
            ("date_group", "TEXT"),
            ("full_filename", "TEXT"),
            ("quick_hash", "TEXT"),
            ("thumbs", "TEXT"),
            ("file_created_at", "DATETIME"),
            ("imported_at", "DATETIME"),
            ("width", "INTEGER"),
            ("height", "INTEGER"),
            ("file_size", "INTEGER"),
            ("mime_type", "TEXT"),
            ("category", "TEXT"),
            ("tags", "TEXT"),
            ("deleted_at", "DATETIME"),
            ("album", "TEXT"),
            ("collection", "TEXT"),
        ]:
            try:
                conn.execute(
                    text(f"ALTER TABLE imageasset ADD COLUMN {column} {col_type}")
                )
                conn.commit()
            except Exception:
                # Column already exists — safe to ignore
                pass

        # Migrate media_path: convert plain strings to JSON arrays
        try:
            rows = conn.execute(
                text("SELECT id, media_path FROM imageasset WHERE media_path IS NOT NULL AND media_path != ''")
            ).fetchall()
            for row_id, mp in rows:
                if mp and not mp.strip().startswith('['):
                    conn.execute(
                        text("UPDATE imageasset SET media_path = :v WHERE id = :id"),
                        {"v": json.dumps([mp]), "id": row_id},
                    )
            conn.commit()
        except Exception:
            pass

        try:
            result = conn.execute(text("PRAGMA table_info(imageasset)"))
            thumb_notnull = any(
                row[1] == "thumb_path" and row[3] == 1 for row in result.fetchall()
            )
            if thumb_notnull:
                conn.execute(text("PRAGMA foreign_keys=OFF"))
                conn.execute(text("""
                    CREATE TABLE imageasset_new (
                        id            INTEGER PRIMARY KEY,
                        original_path TEXT NOT NULL,
                        file_hash     TEXT NOT NULL,
                        thumb_path    TEXT,
                        media_path    TEXT,
                        date_group    TEXT,
                        created_at    DATETIME NOT NULL
                    )
                """))
                conn.execute(text(
                    "INSERT INTO imageasset_new "
                    "SELECT id, original_path, file_hash, thumb_path, "
                    "media_path, date_group, created_at FROM imageasset"
                ))
                conn.execute(text("DROP TABLE imageasset"))
                conn.execute(text("ALTER TABLE imageasset_new RENAME TO imageasset"))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_imageasset_original_path "
                    "ON imageasset(original_path)"
                ))
                conn.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_imageasset_file_hash "
                    "ON imageasset(file_hash)"
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_imageasset_date_group "
                    "ON imageasset(date_group)"
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_imageasset_quick_hash "
                    "ON imageasset(quick_hash)"
                ))
                conn.execute(text("PRAGMA foreign_keys=ON"))
                conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_imageasset_quick_hash "
                "ON imageasset(quick_hash)"
            ))
            conn.commit()
        except Exception:
            pass


def get_session() -> Session:
    return Session(engine)
