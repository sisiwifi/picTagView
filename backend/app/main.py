from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.core.config import CACHE_DIR, MEDIA_DIR, TEMP_DIR
from app.db.session import init_db


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="picTagView Backend", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Serve thumbnail images at /thumbnails/<hash>.webp
    app.mount("/thumbnails", StaticFiles(directory=str(TEMP_DIR)), name="thumbnails")

    # Serve cache thumbnails at /cache/<hash>_cache.webp
    app.mount("/cache", StaticFiles(directory=str(CACHE_DIR)), name="cache")

    # Serve original media files at /media/<date_group>/<filename>
    app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

    app.include_router(api_router)
    return app


app = create_app()
