from __future__ import annotations

from typing import Callable

from web3 import Web3


def namehash(name: str) -> bytes:
    node = b"\x00" * 32
    if not name:
        return node
    labels = [label for label in name.strip(".").split(".") if label]
    for label in reversed(labels):
        node = Web3.keccak(node + Web3.keccak(text=label))
    return node


def resolve_ens_via_registry(
    w3: Web3,
    name: str,
    log: Callable[[str, object], None] | None = None,
) -> str | None:
    registry = "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e"
    registry_abi = [
        {
            "inputs": [{"internalType": "bytes32", "name": "node", "type": "bytes32"}],
            "name": "resolver",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        }
    ]
    resolver_abi = [
        {
            "inputs": [{"internalType": "bytes32", "name": "node", "type": "bytes32"}],
            "name": "addr",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "bytes32", "name": "node", "type": "bytes32"},
                {"internalType": "uint256", "name": "coinType", "type": "uint256"},
            ],
            "name": "addr",
            "outputs": [{"internalType": "bytes", "name": "", "type": "bytes"}],
            "stateMutability": "view",
            "type": "function",
        },
    ]
    node = namehash(name)
    if not node:
        return None
    if log:
        log("ENS registry lookup for {}", name)
    registry_contract = w3.eth.contract(
        address=Web3.to_checksum_address(registry),
        abi=registry_abi,
    )
    try:
        resolver_address = registry_contract.functions.resolver(node).call()
    except Exception as exc:
        if log:
            log("ENS registry lookup failed: {}", exc)
        return None
    if not resolver_address or int(resolver_address, 16) == 0:
        return None
    if log:
        log("ENS resolver contract {}", resolver_address)
    resolver_contract = w3.eth.contract(
        address=Web3.to_checksum_address(resolver_address),
        abi=resolver_abi,
    )
    try:
        resolved = resolver_contract.functions.addr(node).call()
        if resolved and int(resolved, 16) != 0:
            return resolved
    except Exception:
        pass
    try:
        resolved_bytes = resolver_contract.functions.addr(node, 60).call()
        if isinstance(resolved_bytes, (bytes, bytearray)) and len(resolved_bytes) == 20:
            return Web3.to_checksum_address(f"0x{resolved_bytes.hex()}")
    except Exception:
        return None
    return None
