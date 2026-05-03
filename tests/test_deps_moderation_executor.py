from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app.deps import get_moderation_action_executor_service


class DepsModerationExecutorTests(unittest.TestCase):
    """验证审核动作执行器的 dry-run 配置装配。"""

    def test_executor_uses_settings_when_dry_run_not_provided(self) -> None:
        fake_session = SimpleNamespace()
        with patch("app.deps.get_settings", return_value=SimpleNamespace(telegram_action_dry_run=False)):
            executor = get_moderation_action_executor_service(fake_session)

        self.assertFalse(executor._dry_run)


if __name__ == "__main__":
    unittest.main()
