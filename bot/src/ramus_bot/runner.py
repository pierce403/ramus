from __future__ import annotations

import time
from dataclasses import dataclass

from loguru import logger

from .audit import write_decision_report
from .overrides import load_override
from .config import BotConfig
from .evaluator import Evaluator
from .models import BountySpec, Decision
from .poidh.client import PoidhClient
from .state import StateStore


@dataclass(frozen=True)
class RunnerConfig:
    poll_interval_seconds: int = 60
    bounty_reward_wei: int = 0
    min_score_to_award: float = 1.5


class BotRunner:
    def __init__(
        self,
        config: BotConfig,
        runner_config: RunnerConfig,
        poidh: PoidhClient,
        evaluator: Evaluator,
        state: StateStore,
    ) -> None:
        self.config = config
        self.runner_config = runner_config
        self.poidh = poidh
        self.evaluator = evaluator
        self.state = state

    def run_forever(self) -> None:
        logger.info("Starting Ramus bot loop")
        while True:
            self.run_once()
            time.sleep(self.runner_config.poll_interval_seconds)

    def run_once(self) -> None:
        active = self.state.get_active_bounty()
        if not active:
            bounty_id = self._create_default_bounty()
            self.state.create_bounty(bounty_id)
            logger.info("Created bounty {}", bounty_id)
            return

        claims = self.poidh.fetch_claims(active.bounty_id)
        self.state.record_claims(active.bounty_id, claims)
        if not claims:
            logger.info("No claims yet for bounty {}", active.bounty_id)
            return

        decision = self.evaluator.select_winner(active.bounty_id, claims)
        override = load_override(self.config.override_path)
        if override and override.bounty_id == active.bounty_id:
            if override.action == "skip":
                logger.warning("Manual override skip for bounty {}", active.bounty_id)
                return
            if override.claim_id is not None:
                decision = Decision(
                    bounty_id=active.bounty_id,
                    winner_claim_id=override.claim_id,
                    reasoning="Manual override used.",
                    scores=decision.scores,
                )
        self.state.record_decision(decision)
        write_decision_report(decision, claims, self.config.audit_dir)

        max_score = max(decision.scores.values()) if decision.scores else 0.0
        if max_score < self.runner_config.min_score_to_award:
            logger.warning("Score below threshold for bounty {} (score {:.2f}).", active.bounty_id, max_score)
            return

        if decision.winner_claim_id is None:
            logger.info("No winner selected for bounty {}", active.bounty_id)
            return

        tx_hash = self.poidh.accept_claim(active.bounty_id, decision.winner_claim_id)
        self.state.record_payout(active.bounty_id, decision.winner_claim_id, tx_hash)
        self.state.mark_bounty_closed(active.bounty_id)
        logger.info("Accepted claim {} for bounty {} (tx {})", decision.winner_claim_id, active.bounty_id, tx_hash)

    def _create_default_bounty(self) -> int:
        spec = BountySpec(
            title="Clean a local green space",
            description=(
                "Pick up trash in a nearby park or green space and share before/after photos. "
                "Include where you cleaned and how much you collected."
            ),
            reward_wei=self.runner_config.bounty_reward_wei,
            bounty_type="solo",
        )
        return self.poidh.create_bounty(spec)
