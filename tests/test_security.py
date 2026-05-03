from __future__ import annotations

import unittest

from app.utils.security import build_telegram_signature_validator, verify_telegram_secret_token


class TelegramSecretTokenVerificationTests(unittest.TestCase):
    """验证 Telegram Webhook secret token 校验函数的核心行为。"""

    def test_matching_tokens_returns_true(self) -> None:
        """相同 token 应返回 True。"""
        self.assertTrue(verify_telegram_secret_token("mytoken123", "mytoken123"))

    def test_mismatched_tokens_returns_false(self) -> None:
        """不同 token 应返回 False。"""
        self.assertFalse(verify_telegram_secret_token("wrong", "mytoken123"))

    def test_empty_request_token_returns_false(self) -> None:
        """请求 token 为空时应返回 False。"""
        self.assertFalse(verify_telegram_secret_token("", "mytoken123"))

    def test_empty_expected_token_returns_false(self) -> None:
        """期望 token 为空时应返回 False（防止意外放行）。"""
        self.assertFalse(verify_telegram_secret_token("sometoken", ""))

    def test_both_empty_returns_false(self) -> None:
        """两个 token 都为空时应返回 False。"""
        self.assertFalse(verify_telegram_secret_token("", ""))

    def test_signature_validator_factory_valid(self) -> None:
        """build_telegram_signature_validator 生成的校验函数应正确匹配。"""
        validate = build_telegram_signature_validator("secret-abc")
        self.assertTrue(validate({"X-Telegram-Bot-Api-Secret-Token": "secret-abc"}))

    def test_signature_validator_factory_invalid(self) -> None:
        """build_telegram_signature_validator 生成的校验函数应拒绝错误 token。"""
        validate = build_telegram_signature_validator("secret-abc")
        self.assertFalse(validate({"X-Telegram-Bot-Api-Secret-Token": "wrong"}))

    def test_signature_validator_factory_missing_header(self) -> None:
        """请求头缺少 token 字段时应返回 False。"""
        validate = build_telegram_signature_validator("secret-abc")
        self.assertFalse(validate({}))


if __name__ == "__main__":
    unittest.main()