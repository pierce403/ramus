from __future__ import annotations

import os

from decimal import Decimal, InvalidOperation

from eth_account import Account
from loguru import logger
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
    xmtp_wallet_key: str | None
    state_db_path: str
    log_level: str
    bounty_reward_wei: int
    ai_score_endpoint: str | None
    venice_api_key: str | None
    venice_model: str
    venice_base_url: str
    audit_dir: str
    override_path: str | None


class ConfigError(RuntimeError):
    pass


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigError(f"Missing required env var: {name}")
    return value


def _normalize_private_key(value: str) -> str:
    key = value.strip()
    if key and not key.startswith("0x"):
        key = f"0x{key}"
    return key


def _read_key_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        key = _normalize_private_key(handle.read())
    if not key:
        raise ConfigError(f"Wallet key file is empty: {path}")
    return key


def _write_key_file(path: str, key: str) -> None:
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(f"{key}\n")


def _resolve_wallet_key() -> str:
    env_key = os.getenv("WALLET_PRIVATE_KEY")
    xmtp_key = os.getenv("XMTP_WALLET_KEY")
    if env_key and xmtp_key and _normalize_private_key(env_key) != _normalize_private_key(xmtp_key):
        raise ConfigError("WALLET_PRIVATE_KEY and XMTP_WALLET_KEY must match")

    if env_key:
        return _normalize_private_key(env_key)
    if xmtp_key:
        return _normalize_private_key(xmtp_key)

    key_path = os.path.expanduser(os.getenv("WALLET_KEY_PATH", "./state/ramus_wallet.key"))
    if os.path.exists(key_path):
        key = _read_key_file(key_path)
        logger.info("Loaded wallet key from {}", key_path)
        return key

    account = Account.create()
    key = _normalize_private_key(account.key.hex())
    _write_key_file(key_path, key)
    logger.info("Generated new wallet key at {}", key_path)
    return key


def _parse_bounty_reward() -> int:
    raw_wei = os.getenv("BOUNTY_REWARD_WEI")
    raw_eth = os.getenv("BOUNTY_REWARD_ETH")

    if raw_wei:
        try:
            reward = int(raw_wei.strip())
        except ValueError as exc:
            raise ConfigError("Invalid BOUNTY_REWARD_WEI") from exc
        if reward < 0:
            raise ConfigError("BOUNTY_REWARD_WEI must be non-negative")
        return reward

    if raw_eth:
        try:
            reward_eth = Decimal(raw_eth.strip())
        except InvalidOperation as exc:
            raise ConfigError("Invalid BOUNTY_REWARD_ETH") from exc
        if reward_eth < 0:
            raise ConfigError("BOUNTY_REWARD_ETH must be non-negative")
        reward = int(reward_eth * Decimal("1000000000000000000"))
        return reward

    return 0


def load_config() -> BotConfig:
    wallet_private_key = _resolve_wallet_key()
    bounty_reward_wei = _parse_bounty_reward()
    return BotConfig(
        poidh_api_base=os.getenv("POIDH_API_BASE", "https://api.poidh.xyz"),
        poidh_chain_id=int(os.getenv("POIDH_CHAIN_ID", "8453")),
        poidh_chain_slug=os.getenv("POIDH_CHAIN_SLUG", "base"),
        poidh_rpc_url=os.getenv("POIDH_RPC_URL", "https://mainnet.base.org"),
        poidh_api_key=os.getenv("POIDH_API_KEY"),
        wallet_private_key=wallet_private_key,
        wallet_address=os.getenv("WALLET_ADDRESS"),
        xmtp_env=os.getenv("XMTP_ENV", "production"),
        xmtp_db_path=os.getenv("XMTP_DB_PATH", "./.xmtp"),
        xmtp_wallet_key=wallet_private_key,
        state_db_path=os.getenv("STATE_DB_PATH", "./state/ramus.sqlite"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        bounty_reward_wei=bounty_reward_wei,
        ai_score_endpoint=os.getenv("AI_SCORE_ENDPOINT"),
        venice_api_key=os.getenv("VENICE_API_KEY"),
        venice_model=os.getenv("VENICE_MODEL", "llama-3.3-70b"),
        venice_base_url=os.getenv("VENICE_BASE_URL", "https://api.venice.ai/api/v1"),
        audit_dir=os.getenv("AUDIT_DIR", "./docs/bounty-runs"),
        override_path=os.getenv("MANUAL_OVERRIDE_PATH"),
    )
