from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_group_service
from app.exceptions import ResourceNotFoundError
from app.schemas.group import GroupCreate, GroupListResponse, GroupQuery, GroupRead, GroupUpdate

router = APIRouter(prefix="/groups", tags=["groups"])


@router.post(
    "",
    response_model=GroupRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建群组",
    description="创建一个新的群组配置记录，返回创建后的完整群组信息。",
    operation_id="create_group",
)
async def create_group(
    payload: GroupCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> GroupRead:
    """创建群组。"""

    return await get_group_service(session).Create(payload)


@router.get(
    "",
    response_model=GroupListResponse,
    summary="查询群组列表",
    description="按分页条件与启用状态筛选群组列表。",
    operation_id="list_groups",
)
async def list_groups(
    query: Annotated[GroupQuery, Depends()],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> GroupListResponse:
    """查询群组列表。"""

    return await get_group_service(session).FindAll(query)


@router.get(
    "/{group_id}",
    response_model=GroupRead,
    summary="查询群组详情",
    description="按群组主键 ID 查询单个群组详情。",
    operation_id="get_group_by_id",
)
async def get_group_by_id(
    group_id: Annotated[int, Path(..., ge=1, description="群组主键 ID")],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> GroupRead:
    """按主键查询群组详情。"""

    group = await get_group_service(session).FindById(group_id)
    if group is None:
        raise ResourceNotFoundError(resource="群组")
    return group


@router.patch(
    "/{group_id}",
    response_model=GroupRead,
    summary="更新群组",
    description="按群组主键 ID 局部更新群组配置。",
    operation_id="update_group_by_id",
)
async def update_group_by_id(
    group_id: Annotated[int, Path(..., ge=1, description="群组主键 ID")],
    payload: GroupUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> GroupRead:
    """按主键更新群组。"""

    group = await get_group_service(session).UpdateById(group_id, payload)
    if group is None:
        raise ResourceNotFoundError(resource="群组")
    return group


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除群组",
    description="按群组主键 ID 删除群组。删除成功后返回 204，无响应体。",
    operation_id="delete_group_by_id",
    response_description="删除成功，无响应体",
)
async def delete_group_by_id(
    group_id: Annotated[int, Path(..., ge=1, description="群组主键 ID")],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """按主键删除群组。"""

    deleted = await get_group_service(session).DeleteById(group_id)
    if not deleted:
        raise ResourceNotFoundError(resource="群组")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
