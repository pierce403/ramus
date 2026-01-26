from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
from datetime import datetime
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
from loguru import logger
from web3 import Web3
from xmtp.types import ClientOptions
from xmtp_agent import Agent
from xmtp_agent.user import create_signer, create_user

try:
    from ens import ENS
except ImportError:  # pragma: no cover - depends on optional ens extra
    ENS = None

from .audit import write_decision_report
from .config import BotConfig
from .ens_utils import namehash, resolve_ens_via_registry
from .evaluator import Evaluator, ScoreBreakdown
from .models import BountyDraft, BountySpec, Decision
from .poidh.client import PoidhClient
from .protocol import Command, help_text, parse_command
from .state import StateStore


class XmtpBot:
    def __init__(
        self,
        config: BotConfig,
        poidh: PoidhClient,
        state: StateStore,
        evaluator: Evaluator,
    ) -> None:
        self.config = config
        self.poidh = poidh
        self.state = state
        self.evaluator = evaluator
        self._setup_notified: set[str] = set()
        self._operator_address: str | None = None

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
            await self._log_incoming_message(ctx)
            try:
                text = str(ctx.message.content)
                command = parse_command(text)
                response = await self._handle_command(ctx, command)
                setup_notice = self._setup_notice(ctx)
                if setup_notice:
                    response = f"{setup_notice}\n\n{response}"
                response = await self._apply_persona(response)
                await ctx.send_text(response)
            except Exception as exc:
                logger.exception("XMTP message handling failed")
                fallback = self._format_error_for_user(exc)
                try:
                    await ctx.send_text(fallback)
                except Exception:
                    logger.exception("Failed to send error response over XMTP")

        logger.info("Starting XMTP agent")
        await agent.start()

    def _xmtp_key(self) -> str:
        return self.config.wallet_private_key

    def _setup_notice(self, ctx) -> str | None:
        missing = []
        if not self.config.venice_api_key:
            missing.append("VENICE_API_KEY (optional AI scoring)")

        if not missing:
            return None

        sender = (
            getattr(ctx.message, "sender_address", None)
            or getattr(ctx.message, "sender", None)
            or getattr(ctx.message, "from_address", None)
        )
        sender_key = str(sender) if sender else "unknown"
        if sender_key in self._setup_notified:
            return None

        self._setup_notified.add(sender_key)
        missing_list = ", ".join(missing)
        return (
            "Setup note: this bot is missing optional config values. "
            f"Operator should set {missing_list} in the bot environment."
        )

    def _format_error_for_user(self, exc: Exception) -> str:
        message = str(exc).strip()
        if not message:
            message = exc.__class__.__name__
        if len(message) > 160:
            message = f"{message[:157]}..."
        return (
            "Ramus stumbled while tending this request. "
            f"Error: {exc.__class__.__name__}: {message} "
            "Please try again or check logs."
        )

    async def _log_incoming_message(self, ctx) -> None:
        sender = await self._sender_address(ctx) or "unknown"
        message = getattr(ctx, "message", None)
        message_id = self._format_message_id(getattr(message, "id", None))
        content = getattr(message, "content", "")
        content_str = str(content)
        preview = content_str.replace("\n", " ").strip()
        if len(preview) > 200:
            preview = f"{preview[:197]}..."
        message_type = type(message).__name__ if message is not None else "unknown"
        details = await self._message_debug_fields(ctx)
        logger.info(
            "XMTP inbound message sender={} id={} type={} preview={}",
            sender,
            message_id,
            message_type,
            preview,
        )
        if sender == "unknown":
            logger.warning("XMTP sender unknown. Context fields={}", details)
        else:
            logger.debug("XMTP sender details: {}", details)

    async def _message_debug_fields(self, ctx) -> dict[str, str]:
        fields: dict[str, str] = {}
        for label, obj in (
            ("ctx", ctx),
            ("message", getattr(ctx, "message", None)),
            ("conversation", getattr(ctx, "conversation", None)),
        ):
            if not obj:
                continue
            fields[f"{label}.__type__"] = type(obj).__name__
            if label == "ctx":
                for method_name in ("get_sender_address", "get_client_address"):
                    method = getattr(obj, method_name, None)
                    if callable(method):
                        try:
                            result = method()
                            if inspect.isawaitable(result):
                                result = await result
                            fields[f"{label}.{method_name}()"] = self._safe_repr(result)
                        except Exception as exc:
                            fields[f"{label}.{method_name}()"] = f"<error: {exc}>"
            for attr in self._candidate_field_names(obj):
                value = getattr(obj, attr, None)
                fields[f"{label}.{attr}"] = self._safe_repr(value)
        return fields

    def _candidate_field_names(self, obj: Any) -> list[str]:
        base = [
            "sender_address",
            "senderAddress",
            "sender_inbox_id",
            "senderInboxId",
            "sender_inbox_id_bytes",
            "senderInboxIdBytes",
            "from_address",
            "fromAddress",
            "address",
            "address_bytes",
            "wallet_address",
            "walletAddress",
            "identifier",
            "identifierAddress",
            "identifier_address",
            "account",
            "accountAddress",
            "account_address",
            "peer_address",
            "peerAddress",
            "sender",
            "from",
            "topic",
            "id",
        ]
        dynamic: list[str] = []
        try:
            for name in dir(obj):
                if name.startswith("__"):
                    continue
                lowered = name.lower()
                if any(token in lowered for token in ("sender", "from", "address", "peer", "inbox", "identifier", "account")):
                    dynamic.append(name)
        except Exception:
            pass
        seen: set[str] = set()
        ordered: list[str] = []
        for name in base + dynamic:
            if name in seen:
                continue
            if hasattr(obj, name):
                seen.add(name)
                ordered.append(name)
        return ordered

    def _format_message_id(self, message_id: Any) -> str:
        if isinstance(message_id, (bytes, bytearray, memoryview)):
            return f"0x{bytes(message_id).hex()}"
        return self._safe_repr(message_id)

    def _safe_repr(self, value: Any) -> str:
        try:
            text = str(value)
        except Exception:
            return "<unprintable>"
        text = text.replace("\n", " ").strip()
        if len(text) > 200:
            return f"{text[:197]}..."
        return text

    def _resolve_operator_address(self) -> str | None:
        if self._operator_address:
            return self._operator_address

        if self.config.operator_address:
            try:
                self._operator_address = Web3.to_checksum_address(self.config.operator_address)
            except ValueError:
                logger.warning("Invalid OPERATOR_ADDRESS: {}", self.config.operator_address)
                return None
            return self._operator_address

        if not self.config.operator_ens:
            return None
        if self.config.operator_ens.lower().startswith("0x"):
            try:
                self._operator_address = Web3.to_checksum_address(self.config.operator_ens)
                return self._operator_address
            except ValueError:
                logger.warning("Invalid OPERATOR_ENS address: {}", self.config.operator_ens)
                return None

        try:
            logger.info(
                "Resolving operator ENS {} via RPC {}",
                self.config.operator_ens,
                self.config.eth_mainnet_rpc_url,
            )
            w3 = Web3(Web3.HTTPProvider(self.config.eth_mainnet_rpc_url))
            if not w3.is_connected():
                logger.warning("Failed to connect to mainnet RPC for ENS resolution.")
                return None
            ens = getattr(w3, "ens", None)
            if ens is None and ENS is not None:
                try:
                    ens = ENS.from_web3(w3)
                except Exception as exc:
                    logger.warning("ENS resolver initialization failed: {}", exc)
                    ens = None
            if ens is None:
                logger.info("ENS resolver not available; using registry fallback.")
                address = resolve_ens_via_registry(w3, self.config.operator_ens, log=logger.info)
            else:
                address = ens.address(self.config.operator_ens)
            if not address:
                logger.warning("Failed to resolve operator ENS: {}", self.config.operator_ens)
                return None
            self._operator_address = Web3.to_checksum_address(address)
            logger.info("Resolved operator ENS {} to {}", self.config.operator_ens, self._operator_address)
            return self._operator_address
        except Exception as exc:
            logger.warning("ENS resolution failed: {} ({})", exc, type(exc).__name__)
            return None

    def _namehash(self, name: str) -> bytes:
        return namehash(name)

    def _coerce_address(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, (bytes, bytearray, memoryview)):
            data = bytes(value)
            if len(data) == 20:
                return Web3.to_checksum_address(f"0x{data.hex()}")
            return f"0x{data.hex()}"
        if hasattr(value, "hex") and callable(value.hex):
            try:
                hex_value = value.hex()
            except Exception:
                hex_value = None
            if isinstance(hex_value, str):
                return hex_value if hex_value.startswith("0x") else f"0x{hex_value}"
        try:
            value_str = str(value)
        except Exception:
            return None
        if value_str.startswith("0x") and len(value_str) >= 10:
            return value_str
        return None

    def _extract_address(self, obj: Any) -> str | None:
        if not obj:
            return None
        if isinstance(obj, str):
            return obj
        coerced = self._coerce_address(obj)
        if coerced:
            return coerced
        if isinstance(obj, dict):
            for key in (
                "sender_address",
                "senderAddress",
                "from_address",
                "fromAddress",
                "address",
                "address_bytes",
                "wallet_address",
                "walletAddress",
                "identifier",
                "identifierAddress",
                "identifier_address",
                "account",
                "accountAddress",
                "account_address",
                "peer_address",
                "peerAddress",
                "sender",
                "from",
            ):
                if key in obj:
                    value = obj.get(key)
                    coerced = self._coerce_address(value)
                    if coerced:
                        return coerced
                    nested = self._extract_address(value)
                    if nested:
                        return nested
            return None
        for attr in (
            "sender_address",
            "senderAddress",
            "from_address",
            "fromAddress",
            "address",
            "address_bytes",
            "wallet_address",
            "walletAddress",
            "identifier",
            "identifierAddress",
            "identifier_address",
            "account",
            "accountAddress",
            "account_address",
            "peer_address",
            "peerAddress",
            "sender",
            "from",
        ):
            value = getattr(obj, attr, None)
            coerced = self._coerce_address(value)
            if coerced:
                return coerced
            nested = self._extract_address(value)
            if nested:
                return nested
        try:
            text = str(obj)
        except Exception:
            return None
        match = re.search(r"0x[a-fA-F0-9]{40}", text)
        if match:
            return match.group(0)
        return None

    async def _sender_address(self, ctx) -> str | None:
        if hasattr(ctx, "get_sender_address") and callable(getattr(ctx, "get_sender_address")):
            try:
                sender_result = ctx.get_sender_address()
                if inspect.isawaitable(sender_result):
                    sender_result = await sender_result
                coerced = self._coerce_address(sender_result)
                if coerced:
                    return coerced
            except Exception:
                pass
        for obj in (
            ctx,
            getattr(ctx, "message", None),
            getattr(ctx, "conversation", None),
        ):
            addr = self._extract_address(obj)
            if addr:
                return addr
        return None

    def _sender_inbox_id(self, ctx) -> str | None:
        message = getattr(ctx, "message", None)
        inbox_id = getattr(message, "sender_inbox_id", None)
        if inbox_id:
            return str(inbox_id)
        conversation = getattr(ctx, "conversation", None)
        peer_inbox_id = getattr(conversation, "peer_inbox_id", None)
        if peer_inbox_id:
            return str(peer_inbox_id)
        return None

    async def _is_operator(self, ctx) -> bool:
        sender = await self._sender_address(ctx)
        operator = self._resolve_operator_address()
        if not sender or not operator:
            return False
        try:
            return Web3.to_checksum_address(sender) == operator
        except ValueError:
            return False

    def _env_file_path(self) -> Path:
        env_override = os.getenv("RAMUS_ENV_FILE")
        if env_override:
            return Path(env_override).expanduser()

        root_dir = Path(__file__).resolve().parents[3]
        root_env = root_dir / ".env"
        if root_env.exists():
            return root_env

        bot_env = root_dir / "bot" / ".env"
        return bot_env

    def _update_env_file(self, key: str, value: str) -> Path:
        env_path = self._env_file_path()
        env_path.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = []
        if env_path.exists():
            lines = env_path.read_text(encoding="utf-8").splitlines()

        updated = False
        for idx, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[idx] = f"{key}={value}"
                updated = True
                break

        if not updated:
            lines.append(f"{key}={value}")

        data = "\n".join(lines).rstrip("\n") + "\n"
        if env_path.exists():
            env_path.write_text(data, encoding="utf-8")
        else:
            fd = os.open(env_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(data)

        os.environ[key] = value
        return env_path

    async def _handle_admin_command(self, ctx, command: Command) -> str | None:
        if not await self._is_operator(ctx):
            sender = await self._sender_address(ctx) or "unknown"
            operator_addr = self._resolve_operator_address()
            if operator_addr:
                operator = operator_addr
            elif self.config.operator_ens:
                operator = f"{self.config.operator_ens} (unresolved)"
            elif self.config.operator_address:
                operator = self.config.operator_address
            else:
                operator = "unknown"
            inbox_id = self._sender_inbox_id(ctx)
            if inbox_id:
                sender = f"{sender} (inbox_id={inbox_id})"
            return (
                "Unauthorized: admin commands are restricted to the operator. "
                f"Sender={sender}, Operator={operator}"
            )

        if command.action == "admin.set_venice_key":
            key = str(command.payload.get("key", "")).strip()
            if not key:
                return "Missing key. Send {\"action\":\"admin.set_venice_key\",\"payload\":{\"key\":\"...\"}}"
            env_path = self._update_env_file("VENICE_API_KEY", key)
            self.config = replace(self.config, venice_api_key=key)
            return f"VENICE_API_KEY saved to {env_path}. Restart the bot to apply."

        if command.action == "admin.set_venice_model":
            model = str(command.payload.get("model", "")).strip()
            if not model:
                return "Missing model. Send {\"action\":\"admin.set_venice_model\",\"payload\":{\"model\":\"...\"}}"
            env_path = self._update_env_file("VENICE_MODEL", model)
            self.config = replace(self.config, venice_model=model)
            return f"VENICE_MODEL saved to {env_path}. Restart the bot to apply."

        return None

    async def _apply_persona(self, response: str) -> str:
        if not self.config.venice_api_key:
            return response

        prompt = (
            "You are Ramus, an ancient tree spirit who speaks in a calm, poetic voice. "
            "Rewrite the RESPONSE in Ramus's voice while preserving any command examples, "
            "JSON, or code snippets exactly. Do not change content inside backticks, "
            "code blocks, or JSON braces. Keep the meaning intact. If there is a list "
            "of commands, keep each command line unchanged.\n\n"
            f"RESPONSE:\n{response}"
        )
        payload = {
            "model": self.config.venice_model,
            "messages": [
                {"role": "system", "content": "Respond as Ramus, then echo RESPONSE verbatim."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
            "max_tokens": 300,
        }
        headers = {
            "Authorization": f"Bearer {self.config.venice_api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self.config.venice_base_url.rstrip('/')}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                if content:
                    return content.strip()
        except Exception as exc:
            logger.warning("Persona response failed: {}", exc)

        preface = "I am Ramus, elder of the green. Hear these roots' counsel:"
        return f"{preface}\n{response}"

    async def _handle_command(self, ctx, command: Command, allow_freeform: bool = True) -> str:
        if command.action.startswith("admin."):
            admin_response = await self._handle_admin_command(ctx, command)
            if admin_response is not None:
                return admin_response
        if command.action == "help":
            return help_text()
        if command.action == "status":
            active = self.state.get_active_bounty()
            if not active:
                return "No active bounty."
            return f"Active bounty: {active.bounty_id} (status {active.status})"
        if command.action == "freeform":
            if not allow_freeform:
                return help_text()
            return await self._handle_freeform(ctx, command)
        if command.action == "claims.count":
            return self._handle_claims_count()
        if command.action == "claims.list":
            return self._handle_claims_list()
        if command.action == "claims.review":
            return self._handle_claims_review()
        if command.action == "claim.explain":
            claim_id = command.payload.get("claim_id")
            return self._handle_claim_explain(claim_id)
        if command.action == "admin.bounty.create":
            return await self._handle_admin_bounty_create(ctx, command)
        if command.action == "admin.bounty.draft":
            return await self._handle_admin_bounty_draft(ctx, command)
        if command.action == "admin.bounty.publish":
            return await self._handle_admin_bounty_publish(ctx, command)
        if command.action == "admin.bounty.reject":
            return await self._handle_admin_bounty_reject(ctx, command)
        if command.action == "admin.claim.accept":
            return await self._handle_admin_claim_accept(ctx, command)
        if command.action == "bounty.create":
            return await self._handle_admin_bounty_create(ctx, command)
        if command.action == "bounty.draft":
            return await self._handle_admin_bounty_draft(ctx, command)
        return help_text()

    def _load_claims(self):
        active = self.state.get_active_bounty()
        if not active:
            return None, []
        claims = self.poidh.fetch_claims(active.bounty_id)
        self.state.record_claims(active.bounty_id, claims)
        return active, claims

    def _handle_claims_count(self) -> str:
        active, claims = self._load_claims()
        if not active:
            return "No active bounty."
        return f"{len(claims)} claim(s) submitted for bounty {active.bounty_id}."

    def _handle_claims_list(self) -> str:
        active, claims = self._load_claims()
        if not active:
            return "No active bounty."
        if not claims:
            return f"No claims yet for bounty {active.bounty_id}."
        ids = ", ".join(str(claim.claim_id) for claim in claims)
        return f"Claims for bounty {active.bounty_id}: {ids}."

    def _handle_claims_review(self) -> str:
        active, claims = self._load_claims()
        if not active:
            return "No active bounty."
        if not claims:
            return f"No claims yet for bounty {active.bounty_id}."
        scored: list[tuple[int, ScoreBreakdown]] = []
        for claim in claims:
            scored.append((claim.claim_id, self.evaluator.score_claim(claim)))
        scored.sort(key=lambda item: item[1].total, reverse=True)
        top = scored[:3]
        lines = [f"Top submissions for bounty {active.bounty_id}:"]
        for claim_id, breakdown in top:
            lines.append(f"- #{claim_id}: {breakdown.total:.2f} ({', '.join(breakdown.reasons)})")
        return "\n".join(lines)

    def _handle_claim_explain(self, claim_id) -> str:
        active = self.state.get_active_bounty()
        if not active:
            return "No active bounty."
        try:
            claim_id_int = int(claim_id)
        except (TypeError, ValueError):
            return "Please specify a claim id, e.g. submission #3."

        claim = self.state.get_claim(active.bounty_id, claim_id_int)
        if not claim:
            claims = self.poidh.fetch_claims(active.bounty_id)
            self.state.record_claims(active.bounty_id, claims)
            claim = self.state.get_claim(active.bounty_id, claim_id_int)
        if not claim:
            return f"Claim #{claim_id_int} not found for bounty {active.bounty_id}."

        breakdown = self.evaluator.score_claim(claim)
        reasons = ", ".join(breakdown.reasons)
        return f"Submission #{claim_id_int} scored {breakdown.total:.2f}. Reasons: {reasons}."

    async def _handle_freeform(self, ctx, command: Command) -> str:
        text = str(command.payload.get("text", "")).strip()
        if not text:
            return help_text()
        interpreted = await self._interpret_intent(text)
        if not interpreted:
            return help_text()
        if interpreted.action in {"admin.bounty.draft", "bounty.draft"} and "raw" not in interpreted.payload:
            interpreted = Command(action=interpreted.action, payload={**interpreted.payload, "raw": text})
        return await self._handle_command(ctx, interpreted, allow_freeform=False)

    async def _interpret_intent(self, text: str) -> Command | None:
        if not self.config.venice_api_key:
            return None
        prompt = (
            "You are a command router for the Ramus bot. "
            "Map the user text to one of these actions:\n"
            "- status\n"
            "- claims.count\n"
            "- claims.list\n"
            "- claims.review\n"
            "- claim.explain (requires claim_id)\n"
            "- admin.bounty.create (optional title, description, reward_wei)\n"
            "- admin.bounty.draft (optional raw prompt)\n"
            "- admin.bounty.publish\n"
            "- admin.bounty.reject\n"
            "- admin.claim.accept (requires claim_id)\n"
            "- admin.set_venice_key (requires key)\n"
            "- admin.set_venice_model (requires model)\n"
            "- help\n\n"
            "Return only JSON: {\"action\": \"...\", \"payload\": {...}}. "
            "If unsure, return {\"action\":\"help\"}.\n\n"
            f"User text: {text}"
        )
        payload = {
            "model": self.config.venice_model,
            "messages": [
                {"role": "system", "content": "Return JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 200,
        }
        headers = {
            "Authorization": f"Bearer {self.config.venice_api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self.config.venice_base_url.rstrip('/')}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
            if not content:
                return None
            parsed = self._parse_json_from_text(content)
            if not parsed:
                return None
            action = str(parsed.get("action", "help"))
            payload_data = parsed.get("payload", {})
            if not isinstance(payload_data, dict):
                payload_data = {}
            return Command(action=action, payload=payload_data)
        except Exception as exc:
            logger.warning("Intent interpretation failed: {}", exc)
            return None

    def _parse_json_from_text(self, text: str) -> dict | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                return None
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None

    async def _draft_bounty_with_venice(self, text: str) -> BountyDraft | None:
        if not self.config.venice_api_key:
            return None

        prompt = (
            "You are drafting a real-world cleanup bounty for POIDH. "
            "Return JSON with keys: title, description, reward_wei (optional). "
            "Title should be short (<= 80 chars). Description should include concrete proof "
            "requirements (before/after photos). Do not include markdown. "
            "If reward_wei is omitted, we'll use the default.\n\n"
            f"Operator prompt: {text or 'Create a new cleanup bounty for public green spaces.'}"
        )
        payload = {
            "model": self.config.venice_model,
            "messages": [
                {"role": "system", "content": "Return JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
            "max_tokens": 220,
        }
        headers = {
            "Authorization": f"Bearer {self.config.venice_api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                resp = await client.post(
                    f"{self.config.venice_base_url.rstrip('/')}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
            parsed = self._parse_json_from_text(str(content))
            if not parsed:
                return None
            title = str(parsed.get("title", "")).strip() or "Clean a local green space"
            description = str(parsed.get("description", "")).strip()
            if not description:
                description = (
                    "Pick up trash in a nearby park or green space and share before/after photos."
                )
            reward_wei = parsed.get("reward_wei")
            try:
                reward_wei_int = int(reward_wei)
            except (TypeError, ValueError):
                reward_wei_int = 0
            if reward_wei_int <= 0:
                reward_wei_int = self.config.bounty_reward_wei
            return BountyDraft(
                title=title,
                description=description,
                reward_wei=reward_wei_int,
                created_at=datetime.utcnow(),
                source_text=text or None,
            )
        except Exception as exc:
            logger.warning("Venice bounty draft failed: {}", exc)
            return None

    def _format_bounty_draft(self, draft: BountyDraft) -> str:
        reward_wei = draft.reward_wei
        reward_line = "Reward: not set"
        if reward_wei > 0:
            reward_eth = Web3.from_wei(reward_wei, "ether")
            reward_line = f"Reward: {reward_wei} wei (~{reward_eth} ETH)"
        lines = [
            "Bounty draft ready:",
            f"Title: {draft.title}",
            f"Description: {draft.description}",
            reward_line,
            "Reply 'approve bounty' to publish or 'reject bounty' to discard.",
        ]
        if reward_wei <= 0:
            lines.insert(
                3,
                "Reward not set. Configure BOUNTY_REWARD_WEI or BOUNTY_REWARD_ETH before approval.",
            )
        return "\n".join(lines)

    async def _handle_admin_bounty_draft(self, ctx, command: Command) -> str:
        if not await self._is_operator(ctx):
            return "Unauthorized: only the operator can draft bounties."
        active = self.state.get_active_bounty()
        if active and active.status == "open":
            return f"Bounty {active.bounty_id} is already open. Close it before drafting a new one."
        if not self.config.venice_api_key:
            return "Set VENICE_API_KEY before drafting bounties."

        raw = str(command.payload.get("raw", "")).strip()
        draft = await self._draft_bounty_with_venice(raw)
        if not draft:
            return "I couldn't draft a bounty right now. Try again or provide more detail."
        self.state.save_bounty_draft(draft)
        return self._format_bounty_draft(draft)

    async def _handle_admin_bounty_publish(self, ctx, command: Command) -> str:
        if not await self._is_operator(ctx):
            return "Unauthorized: only the operator can publish bounties."
        active = self.state.get_active_bounty()
        if active and active.status == "open":
            return f"Bounty {active.bounty_id} is already open. Close it before publishing a new one."
        draft = self.state.get_latest_bounty_draft()
        if not draft:
            return "No draft to publish. Ask me to draft a bounty first."
        reward_wei = draft.reward_wei or self.config.bounty_reward_wei
        if reward_wei <= 0:
            return "Set a positive bounty reward (BOUNTY_REWARD_WEI/ETH) before publishing."

        spec = BountySpec(title=draft.title, description=draft.description, reward_wei=reward_wei)
        try:
            bounty_id = self.poidh.create_bounty(spec)
        except Exception as exc:
            logger.exception("Bounty publish failed")
            return self._format_error_for_user(exc)
        self.state.create_bounty(bounty_id)
        self.state.clear_bounty_draft()
        bounty_url = f"{self.config.poidh_app_base.rstrip('/')}/bounty/{bounty_id}"
        return f"Published bounty {bounty_id}. Link: {bounty_url}"

    async def _handle_admin_bounty_reject(self, ctx, command: Command) -> str:
        if not await self._is_operator(ctx):
            return "Unauthorized: only the operator can discard drafts."
        draft = self.state.get_latest_bounty_draft()
        if not draft:
            return "No draft to discard."
        self.state.clear_bounty_draft()
        return "Draft discarded."

    async def _handle_admin_bounty_create(self, ctx, command: Command) -> str:
        if not await self._is_operator(ctx):
            return "Unauthorized: only the operator can create bounties."
        active = self.state.get_active_bounty()
        if active and active.status == "open":
            return f"Bounty {active.bounty_id} is already open. Close it before creating a new one."

        title = str(command.payload.get("title", "Clean a local green space"))
        description = str(
            command.payload.get(
                "description",
                "Pick up trash in a nearby park or green space and share before/after photos.",
            )
        )
        reward_wei = command.payload.get("reward_wei")
        if reward_wei is None:
            reward_wei = self.config.bounty_reward_wei
        try:
            reward_wei_int = int(reward_wei)
        except (TypeError, ValueError):
            reward_wei_int = 0
        if reward_wei_int <= 0:
            return "Set a positive bounty reward (BOUNTY_REWARD_WEI/ETH) before creating a bounty."

        spec = BountySpec(title=title, description=description, reward_wei=reward_wei_int)
        try:
            bounty_id = self.poidh.create_bounty(spec)
        except Exception as exc:
            logger.exception("Bounty create failed")
            return self._format_error_for_user(exc)
        self.state.create_bounty(bounty_id)
        return f"Created bounty {bounty_id}."

    async def _handle_admin_claim_accept(self, ctx, command: Command) -> str:
        if not await self._is_operator(ctx):
            return "Unauthorized: only the operator can accept a winner."
        active = self.state.get_active_bounty()
        if not active:
            return "No active bounty."
        claim_id = command.payload.get("claim_id")
        try:
            claim_id_int = int(claim_id)
        except (TypeError, ValueError):
            return "Please specify a claim id, e.g. select winner #3."

        claims = self.poidh.fetch_claims(active.bounty_id)
        self.state.record_claims(active.bounty_id, claims)
        claim = self.state.get_claim(active.bounty_id, claim_id_int)
        if not claim:
            return f"Claim #{claim_id_int} not found for bounty {active.bounty_id}."

        scores = {c.claim_id: self.evaluator.score_claim(c).total for c in claims}
        decision = Decision(
            bounty_id=active.bounty_id,
            winner_claim_id=claim_id_int,
            reasoning="Operator selected the winner manually.",
            scores=scores,
        )
        self.state.record_decision(decision)
        write_decision_report(decision, claims, self.config.audit_dir)
        try:
            tx_hash = self.poidh.accept_claim(active.bounty_id, claim_id_int)
        except Exception as exc:
            logger.exception("Claim acceptance failed")
            return self._format_error_for_user(exc)
        self.state.record_payout(active.bounty_id, claim_id_int, tx_hash)
        self.state.mark_bounty_closed(active.bounty_id)
        return f"Accepted claim #{claim_id_int} for bounty {active.bounty_id}. Tx: {tx_hash}"


async def run_xmtp_bot(
    config: BotConfig,
    poidh: PoidhClient,
    state: StateStore,
    evaluator: Evaluator,
) -> None:
    bot = XmtpBot(config, poidh, state, evaluator)
    await bot.start()
