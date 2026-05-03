from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_rule_service
from app.schemas.rule import RuleCreate, RuleListResponse, RuleQuery, RuleRead, RuleUpdate

router = APIRouter(prefix="/rules", tags=["rules"])


@router.post("", response_model=RuleRead, status_code=status.HTTP_201_CREATED)
async def create_rule(
    payload: RuleCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RuleRead:
    """创建规则。"""

    return await get_rule_service(session).Create(payload)


@router.get("", response_model=RuleListResponse)
async def list_rules(
    query: Annotated[RuleQuery, Depends()],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RuleListResponse:
    """查询规则列表。"""

    return await get_rule_service(session).FindAll(query)


@router.get("/{rule_id}", response_model=RuleRead)
async def get_rule_by_id(
    rule_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RuleRead:
    """按主键查询规则详情。"""

    rule = await get_rule_service(session).FindById(rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则不存在")
    return rule


@router.patch("/{rule_id}", response_model=RuleRead)
async def update_rule_by_id(
    rule_id: int,
    payload: RuleUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RuleRead:
    """按主键更新规则。"""

    rule = await get_rule_service(session).UpdateById(rule_id, payload)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则不存在")
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule_by_id(
    rule_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """按主键删除规则。"""

    deleted = await get_rule_service(session).DeleteById(rule_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则不存在")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
