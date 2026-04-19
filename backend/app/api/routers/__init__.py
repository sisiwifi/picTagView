from app.api.routers.albums import router as albums_router
from app.api.routers.basic import router as basic_router
from app.api.routers.cache import router as cache_router
from app.api.routers.dates import router as dates_router
from app.api.routers.images import router as images_router
from app.api.routers.system import router as system_router
from app.api.routers.tags import router as tags_router
from app.api.routers.trash import router as trash_router

__all__ = [
    "albums_router",
    "basic_router",
    "cache_router",
    "dates_router",
    "images_router",
    "system_router",
    "tags_router",
    "trash_router",
]