from __future__ import annotations

import hmac


def verify_telegram_secret_token(
    request_token: str,
    expected_token: str,
) -> bool:
    """验证 Telegram Webhook 请求中的 X-Telegram-Bot-Api-Secret-Token 头。

    Telegram 在调用 setWebhook 时允许设置 secret_token，
    随后每次推送请求都会在 X-Telegram-Bot-Api-Secret-Token 头中携带该值。
    本函数使用常数时间比较，防止时序攻击。

    Args:
        request_token: 请求头中的 token 值。
        expected_token: 本地配置的预期 token 值。

    Returns:
        bool: token 匹配返回 True，否则返回 False。
    """
    # 任一为空时直接拒绝，避免空字符串比较被绕过
    if not request_token or not expected_token:
        return False
    return hmac.compare_digest(
        request_token.encode("utf-8"),
        expected_token.encode("utf-8"),
    )


def build_telegram_signature_validator(expected_token: str):
    """构造可传入 process_webhook_safely 的签名校验函数。

    生成的函数接受请求头字典并返回是否校验通过，
    可直接作为 validate_signature 参数传入 process_webhook_safely。

    Args:
        expected_token: setWebhook 时配置的 secret_token 字符串。

    Returns:
        Callable[[dict], bool]
    """

    def _validate(headers: dict) -> bool:
        """从请求头 dict 中提取并验证 secret token。"""
        token = headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        return verify_telegram_secret_token(str(token), expected_token)

    return _validate


__all__ = ["verify_telegram_secret_token", "build_telegram_signature_validator"]