from fastapi import APIRouter

from app.api.routers import (
    albums_router,
    basic_router,
    cache_router,
    categories_router,
    dates_router,
    images_router,
    system_router,
    tags_router,
    trash_router,
)

router = APIRouter()
router.include_router(basic_router)
router.include_router(categories_router)
router.include_router(dates_router)
router.include_router(albums_router)
router.include_router(images_router)
router.include_router(system_router)
router.include_router(cache_router)
router.include_router(tags_router)
router.include_router(trash_router)
