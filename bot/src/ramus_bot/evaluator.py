from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class ScoreBreakdown:
    total: float
    reasons: list[str]


class Evaluator:
    def __init__(self, config: EvaluationConfig | None = None) -> None:
        self.config = config or EvaluationConfig()

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
            total += ai_score * self.config.ai_weight
            reasons.append(f"ai_score={ai_score:.2f}")

        return ScoreBreakdown(total=total, reasons=reasons)

    def _ai_score(self, claim: Claim) -> float | None:
        if not self.config.ai_endpoint:
            return None
        payload = {
            "title": claim.title,
            "description": claim.description,
        }
        try:
            response = httpx.post(self.config.ai_endpoint, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            score = float(data.get("score", 0.0))
            return max(0.0, min(1.0, score))
        except Exception:
            return None

    @staticmethod
    def _build_reasoning(breakdowns: dict[int, ScoreBreakdown], winner_id: int | None) -> str:
        if winner_id is None:
            return "No eligible claims found."
        lines = [f"Selected claim {winner_id} with the highest score."]
        for claim_id, breakdown in breakdowns.items():
            lines.append(f"- claim {claim_id}: {breakdown.total:.2f} ({', '.join(breakdown.reasons)})")
        return "\n".join(lines)
