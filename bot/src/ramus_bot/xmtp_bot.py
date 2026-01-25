from __future__ import annotations

import asyncio

from loguru import logger
from xmtp.types import ClientOptions
from xmtp_agent import Agent
from xmtp_agent.user import create_signer, create_user

from .config import BotConfig
from .models import BountySpec
from .poidh.client import PoidhClient
from .protocol import Command, help_text, parse_command
from .state import StateStore


class XmtpBot:
    def __init__(self, config: BotConfig, poidh: PoidhClient, state: StateStore) -> None:
        self.config = config
        self.poidh = poidh
        self.state = state

    async def start(self) -> None:
        user = create_user(self._xmtp_key())
        logger.info("XMTP bot address: {}", user.address)
        signer = create_signer(user)
        agent = await Agent.create(
            signer,
            ClientOptions(
                env=self.config.xmtp_env,
                db_path=self.config.xmtp_db_path,
                disable_history_sync=True,
            ),
        )

        @agent.on("text")
        async def on_text(ctx) -> None:  # type: ignore[override]
            text = str(ctx.message.content)
            command = parse_command(text)
            response = await self._handle_command(command)
            await ctx.send_text(response)

        logger.info("Starting XMTP agent")
        await agent.start()

    def _xmtp_key(self) -> str:
        return self.config.xmtp_wallet_key or self.config.wallet_private_key

    async def _handle_command(self, command: Command) -> str:
        if command.action == "help":
            return help_text()
        if command.action == "status":
            active = self.state.get_active_bounty()
            if not active:
                return "No active bounty."
            return f"Active bounty: {active.bounty_id} (status {active.status})"
        if command.action == "bounty.create":
            title = str(command.payload.get("title", "Clean a local green space"))
            description = str(
                command.payload.get(
                    "description",
                    "Pick up trash in a nearby park or green space and share before/after photos.",
                )
            )
            reward_wei = int(command.payload.get("reward_wei", 0))
            spec = BountySpec(title=title, description=description, reward_wei=reward_wei)
            bounty_id = self.poidh.create_bounty(spec)
            self.state.create_bounty(bounty_id)
            return f"Created bounty {bounty_id}."
        return help_text()


async def run_xmtp_bot(config: BotConfig, poidh: PoidhClient, state: StateStore) -> None:
    bot = XmtpBot(config, poidh, state)
    await bot.start()
