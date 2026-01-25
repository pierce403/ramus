from __future__ import annotations

import asyncio
import os

import pytest
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


async def _resolve_inbox_id(address: str) -> str | None:
    try:
        import xmtp_bindings.xmtpv3 as xv3
        from xmtp.types import ClientOptions
    except Exception as exc:
        pytest.skip(f"XMTP bindings unavailable: {exc}")

    opts = ClientOptions(env=os.getenv("XMTP_ENV", "production"))
    host = opts.resolved_api_url()
    api = await xv3.connect_to_backend(
        host,
        opts.gateway_host,
        host.startswith("https"),
        None,
        opts.app_version,
        None,
        None,
    )
    ffi_identifier = xv3.FfiIdentifier(
        identifier=address,
        identifier_kind=xv3.FfiIdentifierKind.ETHEREUM,
    )
    inbox_id = await xv3.get_inbox_id_for_identifier(api, ffi_identifier)
    return str(inbox_id) if inbox_id else None


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
