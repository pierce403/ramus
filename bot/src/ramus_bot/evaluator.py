from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import Claim, Decision


@dataclass(frozen=True)
class EvaluationConfig:
    min_description_length: int = 30


class Evaluator:
    def __init__(self, config: EvaluationConfig | None = None) -> None:
        self.config = config or EvaluationConfig()

    def select_winner(self, bounty_id: int, claims: Iterable[Claim]) -> Decision:
        scores: dict[int, float] = {}
        winner_id: int | None = None
        for claim in claims:
            score = self._score(claim)
            scores[claim.claim_id] = score
            if winner_id is None or score > scores[winner_id]:
                winner_id = claim.claim_id
        reasoning = self._build_reasoning(scores, winner_id)
        return Decision(bounty_id=bounty_id, winner_claim_id=winner_id, reasoning=reasoning, scores=scores)

    def _score(self, claim: Claim) -> float:
        base = 0.0
        if len(claim.description.strip()) >= self.config.min_description_length:
            base += 1.0
        if "http" in claim.description:
            base += 0.5
        return base

    @staticmethod
    def _build_reasoning(scores: dict[int, float], winner_id: int | None) -> str:
        if winner_id is None:
            return "No eligible claims found."
        return f"Selected claim {winner_id} with the highest score ({scores[winner_id]:.2f})."
