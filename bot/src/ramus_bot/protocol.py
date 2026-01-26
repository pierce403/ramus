from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    action: str
    payload: dict[str, object]


def parse_command(text: str) -> Command:
    stripped = text.strip()
    lowered = stripped.lower()
    tokens = lowered.split()
    if lowered in {"help", "?", "commands"}:
        return Command(action="help", payload={})
    if lowered in {"status", "state"}:
        return Command(action="status", payload={})
    if lowered in {"settings", "config", "configuration", "toggles"}:
        return Command(action="settings", payload={})

    reward_match = re.search(
        r"(?:^|\s)set\s+(?:bounty\s+)?reward\s+([0-9]*\.?[0-9]+)\s*(eth|wei)\b",
        lowered,
    )
    if reward_match:
        amount = reward_match.group(1)
        unit = reward_match.group(2)
        if unit == "wei":
            return Command(action="admin.set_bounty_reward_wei", payload={"reward": amount})
        return Command(action="admin.set_bounty_reward_eth", payload={"reward": amount})
    if "bounty" in lowered and (
        "draft" in lowered
        or "idea" in lowered
        or "suggest" in lowered
        or "propose" in lowered
        or "come up" in lowered
        or "new bounty" in lowered
    ):
        return Command(action="admin.bounty.draft", payload={"raw": stripped})
    if "bounty" in lowered and any(term in lowered for term in ("approve", "publish", "launch", "post")):
        return Command(action="admin.bounty.publish", payload={})
    if "bounty" in lowered and any(term in lowered for term in ("reject", "discard", "cancel")):
        return Command(action="admin.bounty.reject", payload={})
    if "bounty" in lowered and any(term in lowered for term in ("create", "make")):
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
            if key_name in {"infura_key", "infura-key", "infurakey"}:
                parts = stripped.split(None, idx + 1)
                value = parts[idx + 1].strip() if len(parts) > idx + 1 else ""
                return Command(action="admin.set_infura_key", payload={"key": value})
            if key_name in {
                "bounty_reward_wei",
                "reward_wei",
                "bounty_wei",
                "rewardwei",
                "bountyrewardwei",
            }:
                parts = stripped.split(None, idx + 1)
                value = parts[idx + 1].strip() if len(parts) > idx + 1 else ""
                return Command(action="admin.set_bounty_reward_wei", payload={"reward": value})
            if key_name in {
                "bounty_reward_eth",
                "reward_eth",
                "bounty_eth",
                "rewardeth",
                "bountyrewardeth",
            }:
                parts = stripped.split(None, idx + 1)
                value = parts[idx + 1].strip() if len(parts) > idx + 1 else ""
                return Command(action="admin.set_bounty_reward_eth", payload={"reward": value})
            if key_name in {"auto_run", "autorun", "auto-run"}:
                parts = stripped.split(None, idx + 1)
                value = parts[idx + 1].strip() if len(parts) > idx + 1 else ""
                return Command(action="admin.set_auto_run", payload={"enabled": value})

    if "auto run" in lowered or "autorun" in lowered:
        if any(token in lowered for token in ("off", "disable", "disabled", "false", "0")):
            return Command(action="admin.set_auto_run", payload={"enabled": False})
        if any(token in lowered for token in ("on", "enable", "enabled", "true", "1")):
            return Command(action="admin.set_auto_run", payload={"enabled": True})

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

    return Command(action="freeform", payload={"text": stripped})


def help_text() -> str:
    return (
        "Ramus commands:\n"
        "- status\n"
        "- settings\n"
        "- help\n"
        "\n"
        "Operator only:\n"
        "- set venice_key <key>\n"
        "- set venice_model <model>\n"
        "- set infura_key <key>\n"
        "- set bounty_reward_wei <amount>\n"
        "- set bounty_reward_eth <amount>\n"
        "- set auto_run on/off\n"
        "- draft bounty\n"
        "- approve bounty\n"
        "- reject bounty\n"
        "- make bounty\n"
        "- select winner #3"
    )
