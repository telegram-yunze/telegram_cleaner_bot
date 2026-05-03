from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AdDetectResult:
	"""广告检测占位结果。"""

	score: float | None
	reason: str | None = None


class AdDetectorService:
	"""广告检测占位服务，后续可替换为规则融合或模型推理。"""

	async def ScoreText(self, text: str | None) -> AdDetectResult:
		"""返回文本风险分占位结果。"""

		if not text:
			return AdDetectResult(score=None, reason="empty_text")
		return AdDetectResult(score=None, reason="not_implemented")


__all__ = ["AdDetectResult", "AdDetectorService"]
