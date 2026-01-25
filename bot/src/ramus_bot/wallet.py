from __future__ import annotations

from dataclasses import dataclass

from web3 import Web3
from web3.middleware import geth_poa_middleware

from .config import BotConfig


@dataclass(frozen=True)
class BotWallet:
    address: str
    web3: Web3


class WalletError(RuntimeError):
    pass


def init_wallet(config: BotConfig) -> BotWallet:
    web3 = Web3(Web3.HTTPProvider(config.poidh_rpc_url))
    if not web3.is_connected():
        raise WalletError("Failed to connect to RPC")

    # Some POIDH networks use PoA-style headers.
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    account = web3.eth.account.from_key(config.wallet_private_key)
    address = Web3.to_checksum_address(account.address)

    if config.wallet_address and Web3.to_checksum_address(config.wallet_address) != address:
        raise WalletError("WALLET_ADDRESS does not match WALLET_PRIVATE_KEY")

    return BotWallet(address=address, web3=web3)
