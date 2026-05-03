from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_rule_service
from app.exceptions import ResourceNotFoundError
from app.schemas.rule import RuleCreate, RuleListResponse, RuleQuery, RuleRead, RuleUpdate

router = APIRouter(prefix="/rules", tags=["rules"])


@router.post(
    "",
    response_model=RuleRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建规则",
    description="创建一条新的风控规则，返回创建后的规则详情。",
    operation_id="create_rule",
)
async def create_rule(
    payload: RuleCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RuleRead:
    """创建规则。"""

    return await get_rule_service(session).Create(payload)


@router.get(
    "",
    response_model=RuleListResponse,
    summary="查询规则列表",
    description="按群组、启用状态、规则类型等条件分页查询规则。",
    operation_id="list_rules",
)
async def list_rules(
    query: Annotated[RuleQuery, Depends()],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RuleListResponse:
    """查询规则列表。"""

    return await get_rule_service(session).FindAll(query)


@router.get(
    "/{rule_id}",
    response_model=RuleRead,
    summary="查询规则详情",
    description="按规则主键 ID 查询单条规则详情。",
    operation_id="get_rule_by_id",
)
async def get_rule_by_id(
    rule_id: Annotated[int, Path(..., ge=1, description="规则主键 ID")],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RuleRead:
    """按主键查询规则详情。"""

    rule = await get_rule_service(session).FindById(rule_id)
    if rule is None:
        raise ResourceNotFoundError(resource="规则")
    return rule


@router.patch(
    "/{rule_id}",
    response_model=RuleRead,
    summary="更新规则",
    description="按规则主键 ID 局部更新规则字段。",
    operation_id="update_rule_by_id",
)
async def update_rule_by_id(
    rule_id: Annotated[int, Path(..., ge=1, description="规则主键 ID")],
    payload: RuleUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RuleRead:
    """按主键更新规则。"""

    rule = await get_rule_service(session).UpdateById(rule_id, payload)
    if rule is None:
        raise ResourceNotFoundError(resource="规则")
    return rule


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除规则",
    description="按规则主键 ID 删除规则。删除成功后返回 204，无响应体。",
    operation_id="delete_rule_by_id",
    response_description="删除成功，无响应体",
)
async def delete_rule_by_id(
    rule_id: Annotated[int, Path(..., ge=1, description="规则主键 ID")],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """按主键删除规则。"""

    deleted = await get_rule_service(session).DeleteById(rule_id)
    if not deleted:
        raise ResourceNotFoundError(resource="规则")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
