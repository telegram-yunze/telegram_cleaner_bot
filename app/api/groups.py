from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_group_service
from app.schemas.group import GroupCreate, GroupListResponse, GroupQuery, GroupRead, GroupUpdate

router = APIRouter(prefix="/groups", tags=["groups"])


@router.post("", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
async def create_group(
    payload: GroupCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> GroupRead:
    """创建群组。"""

    return await get_group_service(session).Create(payload)


@router.get("", response_model=GroupListResponse)
async def list_groups(
    query: Annotated[GroupQuery, Depends()],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> GroupListResponse:
    """查询群组列表。"""

    return await get_group_service(session).FindAll(query)


@router.get("/{group_id}", response_model=GroupRead)
async def get_group_by_id(
    group_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> GroupRead:
    """按主键查询群组详情。"""

    group = await get_group_service(session).FindById(group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="群组不存在")
    return group


@router.patch("/{group_id}", response_model=GroupRead)
async def update_group_by_id(
    group_id: int,
    payload: GroupUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> GroupRead:
    """按主键更新群组。"""

    group = await get_group_service(session).UpdateById(group_id, payload)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="群组不存在")
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group_by_id(
    group_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """按主键删除群组。"""

    deleted = await get_group_service(session).DeleteById(group_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="群组不存在")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
