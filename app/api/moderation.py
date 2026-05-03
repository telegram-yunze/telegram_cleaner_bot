from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_moderation_service
from app.exceptions import ResourceNotFoundError
from app.schemas.moderation import (
    ModerationRecordCreate,
    ModerationRecordListResponse,
    ModerationRecordQuery,
    ModerationRecordRead,
    ModerationRecordUpdate,
)

router = APIRouter(prefix="/moderation", tags=["moderation"])


@router.post(
    "",
    response_model=ModerationRecordRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建处置记录",
    description="创建一条新的审核处置记录，记录动作、状态与原因等信息。",
    operation_id="create_moderation_record",
)
async def create_moderation_record(
    payload: ModerationRecordCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ModerationRecordRead:
    """创建审核记录。"""

    return await get_moderation_service(session).Create(payload)


@router.get(
    "",
    response_model=ModerationRecordListResponse,
    summary="查询处置记录列表",
    description="按群组与执行状态等条件分页查询处置记录。",
    operation_id="list_moderation_records",
)
async def list_moderation_records(
    query: Annotated[ModerationRecordQuery, Depends()],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ModerationRecordListResponse:
    """查询审核记录列表。"""

    return await get_moderation_service(session).FindAll(query)


@router.get(
    "/{moderation_record_id}",
    response_model=ModerationRecordRead,
    summary="查询处置记录详情",
    description="按处置记录主键 ID 查询单条处置记录详情。",
    operation_id="get_moderation_record_by_id",
)
async def get_moderation_record_by_id(
    moderation_record_id: Annotated[
        int,
        Path(..., ge=1, description="处置记录主键 ID"),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ModerationRecordRead:
    """按主键查询审核记录详情。"""

    record = await get_moderation_service(session).FindById(moderation_record_id)
    if record is None:
        raise ResourceNotFoundError(resource="审核记录")
    return record


@router.patch(
    "/{moderation_record_id}",
    response_model=ModerationRecordRead,
    summary="更新处置记录",
    description="按主键 ID 局部更新处置记录字段。",
    operation_id="update_moderation_record_by_id",
)
async def update_moderation_record_by_id(
    moderation_record_id: Annotated[
        int,
        Path(..., ge=1, description="处置记录主键 ID"),
    ],
    payload: ModerationRecordUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ModerationRecordRead:
    """按主键更新审核记录。"""

    record = await get_moderation_service(session).UpdateById(moderation_record_id, payload)
    if record is None:
        raise ResourceNotFoundError(resource="审核记录")
    return record


@router.patch(
    "/{moderation_record_id}/status",
    response_model=ModerationRecordRead,
    summary="更新处置状态",
    description="按主键 ID 更新处置状态，适用于 pending/success/failed/skipped 流转。",
    operation_id="update_moderation_record_status",
)
async def update_moderation_record_status(
    moderation_record_id: Annotated[
        int,
        Path(..., ge=1, description="处置记录主键 ID"),
    ],
    payload: ModerationRecordUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ModerationRecordRead:
    """按主键更新审核记录执行状态。"""

    record = await get_moderation_service(session).UpdateStatusById(moderation_record_id, payload)
    if record is None:
        raise ResourceNotFoundError(resource="审核记录")
    return record
