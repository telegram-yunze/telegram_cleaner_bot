from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import DetectorReasonToken


@dataclass(slots=True)
class AdDetectResult:
	"""广告检测占位结果。"""

	score: float | None
	reason: str | None = None


class AdDetectorService:
	"""广告检测占位服务，后续可替换为规则融合或模型推理。"""

	async def ScoreText(self, text: str | None) -> AdDetectResult:
		"""返回文本风险分占位结果。

		当前使用简单启发式打分，方便在无模型阶段贯通风险分链路：
		- 空文本：score=None
		- 非空文本：按链接、提及、关键词、文本长度组合估分
		"""

		if not text:
			return AdDetectResult(score=None, reason=DetectorReasonToken.EMPTY_TEXT.value)

		normalized_text = text.strip().lower()
		score = 0.1
		reasons: list[str] = []

		if "http://" in normalized_text or "https://" in normalized_text:
			score += 0.3
			reasons.append(DetectorReasonToken.CONTAINS_LINK.value)

		if "@" in text:
			score += 0.2
			reasons.append(DetectorReasonToken.CONTAINS_MENTION.value)

		ad_keywords = [
			"赌博",
			"彩票",
			"投资",
			"兼职",
			"贷款",
			"充值",
			"优惠",
			"免费",
			"代理",
			"加群",
		]
		if any(keyword in text for keyword in ad_keywords):
			score += 0.3
			reasons.append(DetectorReasonToken.AD_KEYWORDS_DETECTED.value)

		if len(text) <= 12 and ("http://" in normalized_text or "https://" in normalized_text):
			score += 0.15
			reasons.append(DetectorReasonToken.SHORT_TEXT_WITH_LINK.value)

		final_score = round(min(max(score, 0.0), 1.0), 4)
		reason = ",".join(reasons) if reasons else DetectorReasonToken.BASE_SCORE.value
		return AdDetectResult(score=final_score, reason=reason)


__all__ = ["AdDetectResult", "AdDetectorService"]
