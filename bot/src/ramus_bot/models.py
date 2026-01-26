from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class BountySpec:
    title: str
    description: str
    reward_wei: int
    bounty_type: Literal["solo", "open"] = "solo"


@dataclass(frozen=True)
class BountyDraft:
    title: str
    description: str
    reward_wei: int
    created_at: datetime
    source_text: str | None = None


@dataclass(frozen=True)
class Claim:
    claim_id: int
    bounty_id: int
    issuer: str
    bounty_issuer: str
    title: str
    description: str
    created_at: datetime
    accepted: bool


@dataclass(frozen=True)
class Decision:
    bounty_id: int
    winner_claim_id: int | None
    reasoning: str
    scores: dict[int, float]


@dataclass(frozen=True)
class Bounty:
    bounty_id: int
    issuer: str
    title: str
    description: str
    amount_wei: int
    claimer: str
    created_at: datetime
    claim_id: int
