from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BotConfig:
    poidh_api_base: str
    poidh_chain_id: int
    poidh_chain_slug: str
    poidh_rpc_url: str
    poidh_api_key: str | None
    wallet_private_key: str
    wallet_address: str | None
    xmtp_env: str
    xmtp_db_path: str
    state_db_path: str
    log_level: str
    ai_score_endpoint: str | None


class ConfigError(RuntimeError):
    pass


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigError(f"Missing required env var: {name}")
    return value


def load_config() -> BotConfig:
    return BotConfig(
        poidh_api_base=os.getenv("POIDH_API_BASE", "https://api.poidh.xyz"),
        poidh_chain_id=int(os.getenv("POIDH_CHAIN_ID", "8453")),
        poidh_chain_slug=os.getenv("POIDH_CHAIN_SLUG", "base"),
        poidh_rpc_url=_require_env("POIDH_RPC_URL"),
        poidh_api_key=os.getenv("POIDH_API_KEY"),
        wallet_private_key=_require_env("WALLET_PRIVATE_KEY"),
        wallet_address=os.getenv("WALLET_ADDRESS"),
        xmtp_env=os.getenv("XMTP_ENV", "production"),
        xmtp_db_path=os.getenv("XMTP_DB_PATH", "./.xmtp"),
        state_db_path=os.getenv("STATE_DB_PATH", "./state/ramus.sqlite"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        ai_score_endpoint=os.getenv("AI_SCORE_ENDPOINT"),
    )
