from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .models import Claim, Decision


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

    def record_claims(self, bounty_id: int, claims: list[Claim]) -> None:
        raise NotImplementedError

    def record_decision(self, decision: Decision) -> None:
        raise NotImplementedError

    def record_payout(self, bounty_id: int, claim_id: int, tx_hash: str) -> None:
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

    def record_claims(self, bounty_id: int, claims: list[Claim]) -> None:
        # No-op for memory store.
        return None

    def record_decision(self, decision: Decision) -> None:
        self._decisions.append(decision)

    def record_payout(self, bounty_id: int, claim_id: int, tx_hash: str) -> None:
        return None


class SQLiteStateStore(StateStore):
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        cursor = self._conn.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS bounties (
                bounty_id INTEGER PRIMARY KEY,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS claims (
                claim_id INTEGER PRIMARY KEY,
                bounty_id INTEGER NOT NULL,
                issuer TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL,
                accepted INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bounty_id INTEGER NOT NULL,
                winner_claim_id INTEGER,
                reasoning TEXT NOT NULL,
                scores_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS payouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bounty_id INTEGER NOT NULL,
                claim_id INTEGER NOT NULL,
                tx_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def get_active_bounty(self) -> BountyRecord | None:
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT bounty_id, created_at, status FROM bounties WHERE status = 'open' ORDER BY created_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if not row:
            return None
        return BountyRecord(
            bounty_id=row["bounty_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            status=row["status"],
        )

    def create_bounty(self, bounty_id: int) -> BountyRecord:
        created_at = datetime.utcnow().isoformat()
        cursor = self._conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO bounties (bounty_id, created_at, status) VALUES (?, ?, 'open')",
            (bounty_id, created_at),
        )
        self._conn.commit()
        return BountyRecord(bounty_id=bounty_id, created_at=datetime.fromisoformat(created_at), status="open")

    def mark_bounty_closed(self, bounty_id: int) -> None:
        cursor = self._conn.cursor()
        cursor.execute(
            "UPDATE bounties SET status = 'closed' WHERE bounty_id = ?",
            (bounty_id,),
        )
        self._conn.commit()

    def record_claims(self, bounty_id: int, claims: list[Claim]) -> None:
        cursor = self._conn.cursor()
        for claim in claims:
            cursor.execute(
                """
                INSERT OR REPLACE INTO claims
                (claim_id, bounty_id, issuer, title, description, created_at, accepted)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    claim.claim_id,
                    bounty_id,
                    claim.issuer,
                    claim.title,
                    claim.description,
                    claim.created_at.isoformat(),
                    int(claim.accepted),
                ),
            )
        self._conn.commit()

    def record_decision(self, decision: Decision) -> None:
        cursor = self._conn.cursor()
        cursor.execute(
            """
            INSERT INTO decisions (bounty_id, winner_claim_id, reasoning, scores_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                decision.bounty_id,
                decision.winner_claim_id,
                decision.reasoning,
                json.dumps(decision.scores),
                datetime.utcnow().isoformat(),
            ),
        )
        self._conn.commit()

    def record_payout(self, bounty_id: int, claim_id: int, tx_hash: str) -> None:
        cursor = self._conn.cursor()
        cursor.execute(
            """
            INSERT INTO payouts (bounty_id, claim_id, tx_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (bounty_id, claim_id, tx_hash, datetime.utcnow().isoformat()),
        )
        self._conn.commit()
