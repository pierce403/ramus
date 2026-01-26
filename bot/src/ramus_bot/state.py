from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .models import BountyDraft, Claim, Decision


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

    def list_claims(self, bounty_id: int) -> list[Claim]:
        raise NotImplementedError

    def get_claim(self, bounty_id: int, claim_id: int) -> Claim | None:
        raise NotImplementedError

    def record_claims(self, bounty_id: int, claims: list[Claim]) -> None:
        raise NotImplementedError

    def record_decision(self, decision: Decision) -> None:
        raise NotImplementedError

    def list_decisions(self, bounty_id: int) -> list[Decision]:
        raise NotImplementedError

    def record_payout(self, bounty_id: int, claim_id: int, tx_hash: str) -> None:
        raise NotImplementedError

    def save_bounty_draft(self, draft: BountyDraft) -> None:
        raise NotImplementedError

    def get_latest_bounty_draft(self) -> BountyDraft | None:
        raise NotImplementedError

    def clear_bounty_draft(self) -> None:
        raise NotImplementedError

    def bounty_creation_guard(self):
        raise NotImplementedError


class MemoryStateStore(StateStore):
    def __init__(self) -> None:
        self._bounty: BountyRecord | None = None
        self._decisions: list[Decision] = []
        self._claims: dict[int, list[Claim]] = {}
        self._draft: BountyDraft | None = None
        self._creating = False
        self._lock = threading.Lock()

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
        self._claims[bounty_id] = list(claims)

    def list_claims(self, bounty_id: int) -> list[Claim]:
        return list(self._claims.get(bounty_id, []))

    def get_claim(self, bounty_id: int, claim_id: int) -> Claim | None:
        for claim in self._claims.get(bounty_id, []):
            if claim.claim_id == claim_id:
                return claim
        return None

    def record_decision(self, decision: Decision) -> None:
        self._decisions.append(decision)

    def list_decisions(self, bounty_id: int) -> list[Decision]:
        return [decision for decision in self._decisions if decision.bounty_id == bounty_id]

    def record_payout(self, bounty_id: int, claim_id: int, tx_hash: str) -> None:
        return None

    def save_bounty_draft(self, draft: BountyDraft) -> None:
        self._draft = draft

    def get_latest_bounty_draft(self) -> BountyDraft | None:
        return self._draft

    def clear_bounty_draft(self) -> None:
        self._draft = None

    def bounty_creation_guard(self):
        return _BountyCreationGuard(self)


class SQLiteStateStore(StateStore):
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._creating = False
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
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

                CREATE TABLE IF NOT EXISTS bounty_drafts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    reward_wei INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    source_text TEXT
                );
                """
            )
            self._conn.commit()

    def get_active_bounty(self) -> BountyRecord | None:
        with self._lock:
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
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO bounties (bounty_id, created_at, status) VALUES (?, ?, 'open')",
                (bounty_id, created_at),
            )
            self._conn.commit()
        return BountyRecord(bounty_id=bounty_id, created_at=datetime.fromisoformat(created_at), status="open")

    def mark_bounty_closed(self, bounty_id: int) -> None:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "UPDATE bounties SET status = 'closed' WHERE bounty_id = ?",
                (bounty_id,),
            )
            self._conn.commit()

    def record_claims(self, bounty_id: int, claims: list[Claim]) -> None:
        with self._lock:
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

    def list_claims(self, bounty_id: int) -> list[Claim]:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT claim_id, bounty_id, issuer, title, description, created_at, accepted
                FROM claims
                WHERE bounty_id = ?
                ORDER BY created_at ASC
                """,
                (bounty_id,),
            )
            rows = cursor.fetchall()
            claims: list[Claim] = []
            for row in rows:
                claims.append(
                    Claim(
                        claim_id=int(row["claim_id"]),
                        issuer=str(row["issuer"]),
                        bounty_id=int(row["bounty_id"]),
                        bounty_issuer="0x0000000000000000000000000000000000000000",
                        title=str(row["title"]),
                        description=str(row["description"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        accepted=bool(row["accepted"]),
                    )
                )
            return claims

    def get_claim(self, bounty_id: int, claim_id: int) -> Claim | None:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT claim_id, bounty_id, issuer, title, description, created_at, accepted
                FROM claims
                WHERE bounty_id = ? AND claim_id = ?
                LIMIT 1
                """,
                (bounty_id, claim_id),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return Claim(
                claim_id=int(row["claim_id"]),
                issuer=str(row["issuer"]),
                bounty_id=int(row["bounty_id"]),
                bounty_issuer="0x0000000000000000000000000000000000000000",
                title=str(row["title"]),
                description=str(row["description"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                accepted=bool(row["accepted"]),
            )

    def record_decision(self, decision: Decision) -> None:
        with self._lock:
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

    def list_decisions(self, bounty_id: int) -> list[Decision]:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT bounty_id, winner_claim_id, reasoning, scores_json, created_at
                FROM decisions
                WHERE bounty_id = ?
                ORDER BY created_at ASC
                """,
                (bounty_id,),
            )
            rows = cursor.fetchall()
            decisions: list[Decision] = []
            for row in rows:
                decisions.append(
                    Decision(
                        bounty_id=int(row["bounty_id"]),
                        winner_claim_id=row["winner_claim_id"],
                        reasoning=str(row["reasoning"]),
                        scores=json.loads(row["scores_json"]),
                    )
                )
            return decisions

    def record_payout(self, bounty_id: int, claim_id: int, tx_hash: str) -> None:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                INSERT INTO payouts (bounty_id, claim_id, tx_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (bounty_id, claim_id, tx_hash, datetime.utcnow().isoformat()),
            )
            self._conn.commit()

    def save_bounty_draft(self, draft: BountyDraft) -> None:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("DELETE FROM bounty_drafts")
            cursor.execute(
                """
                INSERT INTO bounty_drafts (title, description, reward_wei, created_at, source_text)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    draft.title,
                    draft.description,
                    draft.reward_wei,
                    draft.created_at.isoformat(),
                    draft.source_text,
                ),
            )
            self._conn.commit()

    def get_latest_bounty_draft(self) -> BountyDraft | None:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT title, description, reward_wei, created_at, source_text
                FROM bounty_drafts
                ORDER BY id DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            if not row:
                return None
            return BountyDraft(
                title=str(row["title"]),
                description=str(row["description"]),
                reward_wei=int(row["reward_wei"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                source_text=str(row["source_text"]) if row["source_text"] is not None else None,
            )

    def clear_bounty_draft(self) -> None:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("DELETE FROM bounty_drafts")
            self._conn.commit()

    def bounty_creation_guard(self):
        return _BountyCreationGuard(self)


class _BountyCreationGuard:
    def __init__(self, store: StateStore) -> None:
        self._store = store
        self._entered = False

    def __enter__(self) -> bool:
        if isinstance(self._store, MemoryStateStore):
            return self._enter_memory(self._store)
        if isinstance(self._store, SQLiteStateStore):
            return self._enter_sqlite(self._store)
        raise NotImplementedError("Unsupported state store for bounty_creation_guard")

    def __exit__(self, exc_type, exc, tb) -> None:
        if isinstance(self._store, MemoryStateStore):
            self._exit_memory(self._store)
        elif isinstance(self._store, SQLiteStateStore):
            self._exit_sqlite(self._store)

    def _enter_memory(self, store: MemoryStateStore) -> bool:
        with store._lock:
            if store._creating or (store._bounty and store._bounty.status == "open"):
                return False
            store._creating = True
            self._entered = True
            return True

    def _exit_memory(self, store: MemoryStateStore) -> None:
        if not self._entered:
            return
        with store._lock:
            store._creating = False

    def _enter_sqlite(self, store: SQLiteStateStore) -> bool:
        with store._lock:
            if store._creating:
                return False
            cursor = store._conn.cursor()
            cursor.execute(
                "SELECT 1 FROM bounties WHERE status = 'open' LIMIT 1"
            )
            if cursor.fetchone():
                return False
            store._creating = True
            self._entered = True
            return True

    def _exit_sqlite(self, store: SQLiteStateStore) -> None:
        if not self._entered:
            return
        with store._lock:
            store._creating = False
