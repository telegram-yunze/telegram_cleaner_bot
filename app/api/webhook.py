from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

from app.bot.dispatcher import dispatch_telegram_update
from app.bot.webhook import process_webhook_safely
from app.config import get_settings
from app.utils.security import build_telegram_signature_validator

settings = get_settings()
router = APIRouter(tags=["webhook"])


@router.post(
    settings.webhook_path,
    summary="Telegram Webhook 回调入口",
    description=(
        "接收 Telegram 推送更新并交由 aiogram 处理。"
        "请求头必须携带 X-Telegram-Bot-Api-Secret-Token。"
    ),
    operation_id="telegram_webhook_receive_update",
)
async def telegram_webhook_receive_update(
    request: Request,
    payload: dict[str, Any] = Body(...),
) -> JSONResponse:
    """统一处理 Telegram Webhook 请求。"""

    validator = build_telegram_signature_validator(settings.webhook_secret_token.strip())

    async def _handle_update(raw_payload: dict[str, Any]) -> None:
        await dispatch_telegram_update(raw_payload)

    status_code, body = await process_webhook_safely(
        payload=payload,
        handler=_handle_update,
        validate_signature=lambda _payload: validator(dict(request.headers)),
    )
    return JSONResponse(status_code=status_code, content=body)


__all__ = ["router"]
