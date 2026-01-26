#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BOT_SRC = ROOT_DIR / "bot" / "src"
sys.path.insert(0, str(BOT_SRC))


def _load_env() -> str | None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return None

    env_file = os.getenv("RAMUS_ENV_FILE")
    candidates = []
    if env_file:
        candidates.append(Path(env_file))
    else:
        candidates.extend([ROOT_DIR / ".env", ROOT_DIR / "bot" / ".env"])

    for path in candidates:
        if path and path.exists():
            load_dotenv(path)
            return str(path)
    return None


def _parse_reward(reward_wei: str | None, reward_eth: str | None, default_wei: int) -> int:
    if reward_wei and reward_eth:
        raise ValueError("Provide only one of --reward-wei or --reward-eth.")
    if reward_wei:
        try:
            value = int(reward_wei)
        except ValueError as exc:
            raise ValueError("Invalid --reward-wei (expected integer).") from exc
        if value <= 0:
            raise ValueError("--reward-wei must be positive.")
        return value
    if reward_eth:
        try:
            value = Decimal(reward_eth)
        except InvalidOperation as exc:
            raise ValueError("Invalid --reward-eth (expected decimal).") from exc
        if value <= 0:
            raise ValueError("--reward-eth must be positive.")
        return int(value * Decimal("1000000000000000000"))
    if default_wei > 0:
        return default_wei
    raise ValueError("Reward not set. Provide --reward-wei/--reward-eth or set BOUNTY_REWARD_WEI/ETH.")


def _auto_reward_wei(config, client) -> int:
    from ramus_bot.evaluator import Evaluator
    from ramus_bot.runner import BotRunner, RunnerConfig
    from ramus_bot.runtime import RuntimeSettings
    from ramus_bot.state import MemoryStateStore

    runtime = RuntimeSettings(auto_run=True, bounty_reward_wei=0, bounty_reward_source="none")
    runner = BotRunner(
        config=config,
        runner_config=RunnerConfig(),
        poidh=client,
        evaluator=Evaluator(),
        state=MemoryStateStore(),
        runtime=runtime,
    )
    return runner._default_reward_wei(runtime)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a POIDH bounty directly via Ramus utils.")
    parser.add_argument(
        "--title",
        default="Ramus Grove Stewardship",
        help="Bounty title",
    )
    parser.add_argument(
        "--description",
        default=(
            "Restore a small patch of green space with a mindful cleanup ritual. "
            "Clear litter from a park, trail, or curbside garden, then share "
            "before/after photos and a short note describing what you removed "
            "and where the cleanup took place."
        ),
        help="Bounty description",
    )
    parser.add_argument(
        "--type",
        choices=["solo", "open"],
        default="solo",
        help="Bounty type (default: solo)",
    )
    parser.add_argument("--reward-wei", help="Reward in wei (integer)")
    parser.add_argument("--reward-eth", help="Reward in ETH (decimal)")
    parser.add_argument(
        "--reward-auto",
        action="store_true",
        help="Use the auto default reward (10% of wallet balance) via BotRunner helper",
    )

    args = parser.parse_args()

    env_path = _load_env()
    if env_path:
        print(f"Loaded env from {env_path}")

    try:
        from ramus_bot.config import ConfigError, load_config
        from ramus_bot.models import BountySpec
        from ramus_bot.poidh.client import PoidhClient
        from ramus_bot.wallet import RateLimitError, WalletError, init_wallet
        from web3 import Web3
    except Exception as exc:
        print(f"Failed to import Ramus modules. Ensure deps installed. Error: {exc}")
        return 1

    try:
        config = load_config()
        wallet = init_wallet(config)
        client = PoidhClient(wallet=wallet, config=config)
        if args.reward_auto:
            reward_wei = _auto_reward_wei(config, client)
            if reward_wei <= 0:
                raise ValueError("Auto reward resolved to 0; fund the wallet or set an explicit reward.")
        else:
            reward_wei = _parse_reward(args.reward_wei, args.reward_eth, config.bounty_reward_wei)
        spec = BountySpec(
            title=args.title,
            description=args.description,
            reward_wei=reward_wei,
            bounty_type=args.type,
        )
        reward_eth = Web3.from_wei(reward_wei, "ether")
        print(
            "Creating bounty",
            f"(chain={config.poidh_chain_slug}, wallet={wallet.address}, reward={reward_wei} wei ~ {reward_eth} ETH)",
        )
        bounty_id = client.create_bounty(spec)
        print(f"Created bounty ID: {bounty_id}")
        try:
            bounties = client.fetch_bounties()
            match = next((b for b in bounties if b.bounty_id == bounty_id), None)
            if match:
                print(
                    "Verified onchain bounty:",
                    f"id={match.bounty_id}, issuer={match.issuer}, amount={match.amount_wei} wei,",
                    f"title={match.title!r}",
                )
            else:
                print("Warning: bounty not found via getBounties() yet.")
        except Exception as exc:
            print(f"Warning: failed to verify bounty via getBounties(): {exc}")
        return 0
    except (ConfigError, WalletError, RateLimitError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
