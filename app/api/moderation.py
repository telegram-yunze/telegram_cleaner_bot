from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_moderation_service
from app.schemas.moderation import (
    ModerationRecordCreate,
    ModerationRecordListResponse,
    ModerationRecordQuery,
    ModerationRecordRead,
    ModerationRecordUpdate,
)

router = APIRouter(prefix="/moderation", tags=["moderation"])


@router.post("", response_model=ModerationRecordRead, status_code=status.HTTP_201_CREATED)
async def create_moderation_record(
    payload: ModerationRecordCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ModerationRecordRead:
    """创建审核记录。"""

    return await get_moderation_service(session).Create(payload)


@router.get("", response_model=ModerationRecordListResponse)
async def list_moderation_records(
    query: Annotated[ModerationRecordQuery, Depends()],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ModerationRecordListResponse:
    """查询审核记录列表。"""

    return await get_moderation_service(session).FindAll(query)


@router.get("/{moderation_record_id}", response_model=ModerationRecordRead)
async def get_moderation_record_by_id(
    moderation_record_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ModerationRecordRead:
    """按主键查询审核记录详情。"""

    record = await get_moderation_service(session).FindById(moderation_record_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审核记录不存在")
    return record


@router.patch("/{moderation_record_id}", response_model=ModerationRecordRead)
async def update_moderation_record_by_id(
    moderation_record_id: int,
    payload: ModerationRecordUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ModerationRecordRead:
    """按主键更新审核记录。"""

    record = await get_moderation_service(session).UpdateById(moderation_record_id, payload)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审核记录不存在")
    return record


@router.patch("/{moderation_record_id}/status", response_model=ModerationRecordRead)
async def update_moderation_record_status(
    moderation_record_id: int,
    payload: ModerationRecordUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ModerationRecordRead:
    """按主键更新审核记录执行状态。"""

    record = await get_moderation_service(session).UpdateStatusById(moderation_record_id, payload)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审核记录不存在")
    return record
