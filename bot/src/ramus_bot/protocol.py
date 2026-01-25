from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    action: str
    payload: dict[str, object]


def parse_command(text: str) -> Command:
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            action = str(data.get("action", "help"))
            payload = data.get("payload", {}) if isinstance(data.get("payload", {}), dict) else {}
            return Command(action=action, payload=payload)
        except json.JSONDecodeError:
            pass

    lowered = stripped.lower()
    if lowered in {"help", "?", "commands"}:
        return Command(action="help", payload={})
    if lowered in {"status", "state"}:
        return Command(action="status", payload={})
    if lowered.startswith("create"):
        return Command(action="bounty.create", payload={"raw": stripped})

    return Command(action="help", payload={})


def help_text() -> str:
    return (
        "Ramus commands:\n"
        "- status\n"
        "- help\n"
        "- send JSON: {\"action\": \"bounty.create\", \"payload\": {\"title\": ..., \"description\": ..., \"reward_wei\": ...}}"
    )
