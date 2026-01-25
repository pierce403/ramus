from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Iterable

import httpx

from .models import Claim, Decision


@dataclass(frozen=True)
class EvaluationConfig:
    min_description_length: int = 40
    url_bonus: float = 1.0
    before_after_bonus: float = 1.0
    location_bonus: float = 0.5
    ai_weight: float = 0.5
    ai_endpoint: str | None = None
    venice_api_key: str | None = None
    venice_model: str = "llama-3.3-70b"
    venice_base_url: str = "https://api.venice.ai/api/v1"
    venice_timeout_seconds: int = 15


@dataclass(frozen=True)
class ScoreBreakdown:
    total: float
    reasons: list[str]


@dataclass(frozen=True)
class AiScore:
    score: float
    reason: str | None = None


class Evaluator:
    def __init__(self, config: EvaluationConfig | None = None) -> None:
        self.config = config or EvaluationConfig()

    def score_claim(self, claim: Claim) -> ScoreBreakdown:
        return self._score(claim)

    def select_winner(self, bounty_id: int, claims: Iterable[Claim]) -> Decision:
        scores: dict[int, float] = {}
        breakdowns: dict[int, ScoreBreakdown] = {}
        winner_id: int | None = None
        for claim in claims:
            breakdown = self._score(claim)
            breakdowns[claim.claim_id] = breakdown
            scores[claim.claim_id] = breakdown.total
            if winner_id is None or breakdown.total > scores[winner_id]:
                winner_id = claim.claim_id

        reasoning = self._build_reasoning(breakdowns, winner_id)
        return Decision(bounty_id=bounty_id, winner_claim_id=winner_id, reasoning=reasoning, scores=scores)

    def _score(self, claim: Claim) -> ScoreBreakdown:
        reasons: list[str] = []
        total = 0.0
        description = claim.description.strip()
        title = claim.title.strip().lower()
        lower = description.lower()

        if len(description) >= self.config.min_description_length:
            total += 1.0
            reasons.append("clear description")
        else:
            reasons.append("short description")

        if "http" in description:
            total += self.config.url_bonus
            reasons.append("includes link")

        if "before" in lower and "after" in lower:
            total += self.config.before_after_bonus
            reasons.append("mentions before/after")

        if any(token in lower for token in ["park", "trail", "street", "river", "beach", "neighborhood"]):
            total += self.config.location_bonus
            reasons.append("mentions location")

        ai_score = self._ai_score(claim)
        if ai_score is not None:
            total += ai_score.score * self.config.ai_weight
            reason = f"ai_score={ai_score.score:.2f}"
            if ai_score.reason:
                clipped = ai_score.reason.strip()
                if len(clipped) > 140:
                    clipped = f"{clipped[:137]}..."
                reason = f"{reason} ({clipped})"
            reasons.append(reason)

        return ScoreBreakdown(total=total, reasons=reasons)

    def _ai_score(self, claim: Claim) -> AiScore | None:
        if self.config.ai_endpoint:
            return self._score_via_endpoint(claim)
        if self.config.venice_api_key:
            return self._score_via_venice(claim)
        return None

    def _score_via_endpoint(self, claim: Claim) -> AiScore | None:
        payload = {
            "title": claim.title,
            "description": claim.description,
        }
        try:
            response = httpx.post(self.config.ai_endpoint, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            return self._score_from_payload(data)
        except Exception:
            return None

    def _score_via_venice(self, claim: Claim) -> AiScore | None:
        prompt = (
            "You are judging a real-world cleanup bounty claim. "
            "Score quality from 0 to 1. Respond with JSON only, "
            'format: {"score": 0.0, "reason": "short reason"}.\n\n'
            f"Title: {claim.title}\n"
            f"Description: {claim.description}"
        )
        payload = {
            "model": self.config.venice_model,
            "messages": [
                {"role": "system", "content": "Return JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 200,
        }
        headers = {
            "Authorization": f"Bearer {self.config.venice_api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = httpx.post(
                f"{self.config.venice_base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.config.venice_timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return self._score_from_text(content)
        except Exception:
            return None

    def _score_from_text(self, text: str) -> AiScore | None:
        raw = text.strip()
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return self._score_from_payload(data)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                return None
            try:
                data = json.loads(match.group(0))
                return self._score_from_payload(data)
            except json.JSONDecodeError:
                return None

    @staticmethod
    def _score_from_payload(data: dict) -> AiScore | None:
        try:
            score_raw = data.get("score")
            if score_raw is None:
                return None
            score = float(score_raw)
        except (TypeError, ValueError):
            return None
        score = max(0.0, min(1.0, score))
        reason = data.get("reason")
        if isinstance(reason, str):
            reason = reason.strip()
        else:
            reason = None
        return AiScore(score=score, reason=reason)

    @staticmethod
    def _build_reasoning(breakdowns: dict[int, ScoreBreakdown], winner_id: int | None) -> str:
        if winner_id is None:
            return "No eligible claims found."
        lines = [f"Selected claim {winner_id} with the highest score."]
        for claim_id, breakdown in breakdowns.items():
            lines.append(f"- claim {claim_id}: {breakdown.total:.2f} ({', '.join(breakdown.reasons)})")
        return "\n".join(lines)
