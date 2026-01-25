from __future__ import annotations

import asyncio

from loguru import logger

from .config import load_config
from .evaluator import Evaluator, EvaluationConfig
from .poidh.client import PoidhClient
from .runner import BotRunner, RunnerConfig
from .state import SQLiteStateStore
from .wallet import init_wallet
from .xmtp_bot import run_xmtp_bot


def build_runner(config) -> BotRunner:
    wallet = init_wallet(config)
    runner_config = RunnerConfig(poll_interval_seconds=60, bounty_reward_wei=0)
    poidh = PoidhClient(wallet=wallet, config=config)
    evaluator = Evaluator(
        EvaluationConfig(
            ai_endpoint=config.ai_score_endpoint,
            venice_api_key=config.venice_api_key,
            venice_model=config.venice_model,
            venice_base_url=config.venice_base_url,
        )
    )
    state = SQLiteStateStore(config.state_db_path)
    return BotRunner(
        config=config,
        runner_config=runner_config,
        poidh=poidh,
        evaluator=evaluator,
        state=state,
    )


async def main() -> None:
    config = load_config()
    runner = build_runner(config)
    await asyncio.gather(
        run_xmtp_bot(config, runner.poidh, runner.state),
        asyncio.to_thread(runner.run_forever),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        logger.exception("Ramus bot crashed: {}", exc)
        raise
