from __future__ import annotations

import asyncio
import inspect
import os
import tempfile
from typing import Any

import pytest
from eth_account import Account
from web3 import Web3

from ramus_bot.ens_utils import resolve_ens_via_registry


RUN_IDENTITY_TESTS = os.getenv("RUN_IDENTITY_TESTS") == "1"


def _require_identity_tests() -> None:
    if not RUN_IDENTITY_TESTS:
        pytest.skip("Set RUN_IDENTITY_TESTS=1 to run identity integration tests.")


def _resolve_deanpierce_address() -> str:
    rpc_url = os.getenv("ETH_MAINNET_RPC_URL", "https://cloudflare-eth.com")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        pytest.skip("ETH_MAINNET_RPC_URL is not reachable.")
    address = resolve_ens_via_registry(w3, "deanpierce.eth")
    if not address:
        pytest.fail("Failed to resolve deanpierce.eth via registry fallback.")
    return address


def _identifier_kind() -> Any:
    try:
        from xmtp.types import IdentifierKind
    except Exception:
        return "Ethereum"
    for attr in ("Ethereum", "ETHEREUM", "ethereum"):
        if hasattr(IdentifierKind, attr):
            return getattr(IdentifierKind, attr)
    return "Ethereum"


async def _resolve_inbox_id(address: str) -> str | None:
    try:
        from xmtp_agent import Agent
        from xmtp_agent.user import create_signer, create_user
        from xmtp.types import ClientOptions
    except Exception as exc:
        pytest.skip(f"XMTP dependencies unavailable: {exc}")

    account = Account.create()
    wallet_key = account.key.hex()
    if not wallet_key.startswith("0x"):
        wallet_key = f"0x{wallet_key}"
    user = create_user(wallet_key)
    signer = create_signer(user)
    with tempfile.TemporaryDirectory() as temp_dir:
        agent = await Agent.create(
            signer,
            ClientOptions(
                env=os.getenv("XMTP_ENV", "production"),
                db_path=temp_dir,
                disable_history_sync=True,
            ),
        )
        client = getattr(agent, "client", None) or getattr(agent, "_client", None)
        if client is None:
            pytest.skip("XMTP client not available on Agent.")

        kind = _identifier_kind()
        method_names = ("get_inbox_id_by_identifier", "getInboxIdByIdentifier")
        for method_name in method_names:
            method = getattr(client, method_name, None)
            if not method:
                continue
            call_variants = [
                ((), {"identifier": address, "identifierKind": kind}),
                ((), {"identifier": address, "identifier_kind": kind}),
                ((address, kind), {}),
                ((address,), {"identifier_kind": kind}),
            ]
            for args, kwargs in call_variants:
                try:
                    result = method(*args, **kwargs)
                except TypeError:
                    continue
                if inspect.isawaitable(result):
                    result = await result
                if result:
                    return str(result)
        pytest.skip("No inbox id lookup method found on XMTP client.")

    return None


@pytest.mark.integration
def test_resolve_ens_registry() -> None:
    _require_identity_tests()
    address = _resolve_deanpierce_address()
    assert address.startswith("0x") and len(address) == 42


@pytest.mark.integration
def test_xmtp_inbox_for_deanpierce() -> None:
    _require_identity_tests()
    address = _resolve_deanpierce_address()
    inbox_id = asyncio.run(_resolve_inbox_id(address))
    assert inbox_id is not None
    print(f"deanpierce.eth inbox id: {inbox_id}")
