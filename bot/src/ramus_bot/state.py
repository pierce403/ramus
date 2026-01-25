from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .models import Decision


@dataclass(frozen=True)
class BountyRecord:
    bounty_id: int
    created_at: datetime
    status: str


class StateStore:
    def get_active_bounty(self) -> BountyRecord | None:
        raise NotImplementedError

    def create_bounty(self, bounty_id: int) -> BountyRecord:
        raise NotImplementedError

    def mark_bounty_closed(self, bounty_id: int) -> None:
        raise NotImplementedError

    def record_decision(self, decision: Decision) -> None:
        raise NotImplementedError


class MemoryStateStore(StateStore):
    def __init__(self) -> None:
        self._bounty: BountyRecord | None = None
        self._decisions: list[Decision] = []

    def get_active_bounty(self) -> BountyRecord | None:
        if self._bounty and self._bounty.status == "open":
            return self._bounty
        return None

    def create_bounty(self, bounty_id: int) -> BountyRecord:
        record = BountyRecord(bounty_id=bounty_id, created_at=datetime.utcnow(), status="open")
        self._bounty = record
        return record

    def mark_bounty_closed(self, bounty_id: int) -> None:
        if self._bounty and self._bounty.bounty_id == bounty_id:
            self._bounty = BountyRecord(
                bounty_id=bounty_id, created_at=self._bounty.created_at, status="closed"
            )

    def record_decision(self, decision: Decision) -> None:
        self._decisions.append(decision)
