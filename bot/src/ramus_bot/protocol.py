from __future__ import annotations

import json
import re
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
    tokens = lowered.split()
    if lowered in {"help", "?", "commands"}:
        return Command(action="help", payload={})
    if lowered in {"status", "state"}:
        return Command(action="status", payload={})
    if "bounty" in lowered and any(term in lowered for term in ("create", "make", "new")):
        return Command(action="admin.bounty.create", payload={"raw": stripped})
    if tokens and tokens[0] in {"set", "admin"}:
        idx = 1 if tokens[0] == "set" else 2
        if len(tokens) > idx:
            key_name = tokens[idx]
            if key_name in {"venice_key", "venice-key", "venicekey"}:
                parts = stripped.split(None, idx + 1)
                value = parts[idx + 1].strip() if len(parts) > idx + 1 else ""
                return Command(action="admin.set_venice_key", payload={"key": value})
            if key_name in {"venice_model", "venice-model", "venicemodel"}:
                parts = stripped.split(None, idx + 1)
                value = parts[idx + 1].strip() if len(parts) > idx + 1 else ""
                return Command(action="admin.set_venice_model", payload={"model": value})

    if "claim" in lowered or "submission" in lowered or "winner" in lowered:
        match = re.search(r"(submission|claim|winner)\s*#?\s*(\d+)", lowered)
        if match:
            claim_id = int(match.group(2))
            if any(term in lowered for term in ("select", "pick", "choose", "accept", "approve")):
                return Command(action="admin.claim.accept", payload={"claim_id": claim_id})
            if "wrong" in lowered or "why" in lowered or "what was" in lowered:
                return Command(action="claim.explain", payload={"claim_id": claim_id})
            return Command(action="claim.explain", payload={"claim_id": claim_id})

    if "how many" in lowered and "claim" in lowered:
        return Command(action="claims.count", payload={})

    if "list" in lowered and "claim" in lowered:
        return Command(action="claims.list", payload={})

    if "look good" in lowered or "best" in lowered or "top" in lowered:
        if "claim" in lowered or "submission" in lowered:
            return Command(action="claims.review", payload={})

    return Command(action="help", payload={})


def help_text() -> str:
    return (
        "Ramus commands:\n"
        "- status\n"
        "- help\n"
        "- send JSON: {\"action\": \"bounty.create\", \"payload\": {\"title\": ..., \"description\": ..., \"reward_wei\": ...}}\n"
        "- admin JSON: {\"action\": \"admin.set_venice_key\", \"payload\": {\"key\": \"...\"}}\n"
        "- admin JSON: {\"action\": \"admin.set_venice_model\", \"payload\": {\"model\": \"...\"}}\n"
        "- admin text: set venice_key <key>\n"
        "- admin text: set venice_model <model>\n"
        "- admin text: make bounty\n"
        "- admin text: select winner #3\n"
        "- ask: how many claims have been submitted?\n"
        "- ask: are there any that look good?\n"
        "- ask: what was wrong with submission #3?"
    )
