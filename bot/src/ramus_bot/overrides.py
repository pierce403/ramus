from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class ManualOverride:
    bounty_id: int
    action: Literal["accept", "skip"]
    claim_id: int | None


def load_override(path: str | None) -> ManualOverride | None:
    if not path:
        return None
    override_path = Path(path)
    if not override_path.exists():
        return None
    data = json.loads(override_path.read_text())
    return ManualOverride(
        bounty_id=int(data["bounty_id"]),
        action=data.get("action", "accept"),
        claim_id=data.get("claim_id"),
    )
