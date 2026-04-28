from fastapi import APIRouter

from app.api.schemas import (
    TrashActionResult,
    TrashHardDeleteRequest,
    TrashListResponse,
    TrashMoveRequest,
    TrashRestoreRequest,
)
from app.services.trash_service import (
    clear_trash,
    hard_delete_trash_entries,
    list_trash_items,
    move_targets_to_trash,
    reconcile_trash_items,
    restore_trash_entries,
)

router = APIRouter()


@router.get("/api/trash/items", response_model=TrashListResponse)
def trash_items() -> TrashListResponse:
    return list_trash_items()


@router.post("/api/trash/reconcile")
def trash_reconcile() -> dict[str, int | bool]:
    return reconcile_trash_items()


@router.post("/api/trash/move", response_model=TrashActionResult)
def trash_move(request: TrashMoveRequest) -> TrashActionResult:
    return move_targets_to_trash(request.items)


@router.post("/api/trash/restore", response_model=TrashActionResult)
def trash_restore(request: TrashRestoreRequest) -> TrashActionResult:
    return restore_trash_entries(request.entry_ids)


@router.post("/api/trash/hard-delete", response_model=TrashActionResult)
def trash_hard_delete(request: TrashHardDeleteRequest) -> TrashActionResult:
    return hard_delete_trash_entries(request.entry_ids)


@router.delete("/api/trash", response_model=TrashActionResult)
def trash_clear() -> TrashActionResult:
    return clear_trash()