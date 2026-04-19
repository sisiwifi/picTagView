import json

from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text

from app.core.config import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

_db_initialized = False


def init_db() -> None:
    global _db_initialized
    if _db_initialized:
        return
    # Import all models so SQLModel.metadata knows every table before create_all.
    from app.models.album import Album          # noqa: F401
    from app.models.album_image import AlbumImage  # noqa: F401
    from app.models.tag import Tag              # noqa: F401
    from app.models.trash_entry import TrashEntry  # noqa: F401
    SQLModel.metadata.create_all(engine)
    _migrate_db()
    _db_initialized = True


def _migrate_db() -> None:
    """Add new columns to existing tables if they don't exist yet.

    Only additive (ALTER TABLE ADD COLUMN) migrations are performed here.
    Destructive schema changes (e.g. removing deleted_at) are left to the
    caller who will drop-and-recreate the DB when clearing all data.
    """
    with engine.connect() as conn:
        # ── imageasset columns ────────────────────────────────────────────
        for column, col_type in [
            ("media_path",     "TEXT"),
            ("date_group",     "TEXT"),
            ("full_filename",  "TEXT"),
            ("quick_hash",     "TEXT"),
            ("thumbs",         "TEXT"),
            ("file_created_at","DATETIME"),
            ("imported_at",    "DATETIME"),
            ("width",          "INTEGER"),
            ("height",         "INTEGER"),
            ("file_size",      "INTEGER"),
            ("mime_type",      "TEXT"),
            ("category",       "TEXT"),
            ("tags",           "TEXT"),
            ("album",          "TEXT"),
            ("collection",     "TEXT"),
        ]:
            try:
                conn.execute(
                    text(f"ALTER TABLE imageasset ADD COLUMN {column} {col_type}")
                )
                conn.commit()
            except Exception:
                pass  # Column already exists — safe to ignore

        # ── Migrate media_path: convert plain strings to JSON arrays ──────
        try:
            rows = conn.execute(
                text(
                    "SELECT id, media_path FROM imageasset "
                    "WHERE media_path IS NOT NULL AND media_path != ''"
                )
            ).fetchall()
            for row_id, mp in rows:
                if mp and not mp.strip().startswith("["):
                    conn.execute(
                        text("UPDATE imageasset SET media_path = :v WHERE id = :id"),
                        {"v": json.dumps([mp]), "id": row_id},
                    )
            conn.commit()
        except Exception:
            pass

        # ── Legacy: relax thumb_path NOT NULL constraint if present ───────
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
                for idx_sql in [
                    "CREATE INDEX IF NOT EXISTS ix_imageasset_original_path ON imageasset(original_path)",
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_imageasset_file_hash ON imageasset(file_hash)",
                    "CREATE INDEX IF NOT EXISTS ix_imageasset_date_group ON imageasset(date_group)",
                    "CREATE INDEX IF NOT EXISTS ix_imageasset_quick_hash ON imageasset(quick_hash)",
                ]:
                    conn.execute(text(idx_sql))
                conn.execute(text("PRAGMA foreign_keys=ON"))
                conn.commit()
        except Exception:
            pass

        # ── Ensure quick_hash index ───────────────────────────────────────
        try:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_imageasset_quick_hash "
                "ON imageasset(quick_hash)"
            ))
            conn.commit()
        except Exception:
            pass

        # ── tag columns ───────────────────────────────────────────────────
        for column, col_type in [
            ("public_id",    "TEXT"),
            ("display_name", "TEXT"),
            ("type",         "TEXT"),
            ("description",  "TEXT"),
            ("category",     "TEXT"),
            ("usage_count",  "INTEGER"),
            ("last_used_at", "TEXT"),
            ("metadata",     "TEXT"),
            ("created_by",   "TEXT"),
            ("updated_at",   "DATETIME"),
        ]:
            try:
                conn.execute(
                    text(f"ALTER TABLE tag ADD COLUMN {column} {col_type}")
                )
                conn.commit()
            except Exception:
                pass

        try:
            conn.execute(text("UPDATE tag SET type = 'normal' WHERE type IS NULL OR trim(type) = ''"))
            conn.commit()
        except Exception:
            pass

        # ── album_image table indexes & constraints ──────────────────────
        try:
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_album_image_album_image "
                "ON album_image(album_id, image_id)"
            ))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_album_image_image_id "
                "ON album_image(image_id)"
            ))
            conn.commit()
        except Exception:
            pass

        # ── album columns ─────────────────────────────────────────────────
        for column, col_type in [
            ("public_id",            "TEXT"),
            ("title",                "TEXT"),
            ("description",          "TEXT"),
            ("path",                 "TEXT"),
            ("category",             "TEXT"),
            ("is_leaf",              "INTEGER"),
            ("parent_id",            "INTEGER"),
            ("cover",                "TEXT"),
            ("photo_count",          "INTEGER"),
            ("subtree_photo_count",  "INTEGER"),
            ("sort_mode",            "TEXT"),
            ("settings",             "TEXT"),
            ("stats",                "TEXT"),
            ("date_group",           "TEXT"),
            ("created_at",           "DATETIME"),
            ("updated_at",           "DATETIME"),
        ]:
            try:
                conn.execute(
                    text(f"ALTER TABLE album ADD COLUMN {column} {col_type}")
                )
                conn.commit()
            except Exception:
                pass


def get_session() -> Session:
    return Session(engine)
