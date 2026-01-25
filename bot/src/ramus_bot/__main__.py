from __future__ import annotations

from loguru import logger

from .config import load_config
from .evaluator import Evaluator, EvaluationConfig
from .poidh.client import PoidhClient
from .runner import BotRunner, RunnerConfig
from .state import MemoryStateStore
from .wallet import init_wallet


def main() -> None:
    config = load_config()
    wallet = init_wallet(config)
    runner_config = RunnerConfig(poll_interval_seconds=60, bounty_reward_wei=0)
    poidh = PoidhClient(wallet=wallet, config=config)
    evaluator = Evaluator(EvaluationConfig(ai_endpoint=config.ai_score_endpoint))
    state = MemoryStateStore()

    runner = BotRunner(
        config=config,
        runner_config=runner_config,
        poidh=poidh,
        evaluator=evaluator,
        state=state,
    )
    runner.run_forever()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logger.exception("Ramus bot crashed: {}", exc)
        raise
