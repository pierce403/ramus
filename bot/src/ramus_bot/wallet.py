from __future__ import annotations

from dataclasses import dataclass
import time

from web3 import Web3
from web3.providers.rpc import HTTPProvider
from loguru import logger

try:
    import requests
except ImportError:  # pragma: no cover - requests is a web3 dependency
    requests = None

try:
    from web3.middleware import geth_poa_middleware
except ImportError:  # pragma: no cover - depends on web3 version
    try:
        from web3.middleware.geth_poa import geth_poa_middleware
    except ImportError:  # pragma: no cover - depends on web3 version
        try:
            from web3.middleware.poa import geth_poa_middleware
        except ImportError:  # pragma: no cover - depends on web3 version
            try:
                from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
            except ImportError:  # pragma: no cover - depends on web3 version
                geth_poa_middleware = None

from .config import BotConfig


@dataclass(frozen=True)
class BotWallet:
    address: str
    web3: Web3


class WalletError(RuntimeError):
    pass


class RetryingHTTPProvider(HTTPProvider):
    def __init__(self, *args, max_retries: int = 3, backoff_seconds: float = 1.0, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds

    def make_request(self, method, params):  # type: ignore[override]
        delay = self._backoff_seconds
        for attempt in range(1, self._max_retries + 1):
            try:
                return super().make_request(method, params)
            except Exception as exc:
                if not _is_rate_limit_error(exc) or attempt >= self._max_retries:
                    raise
                logger.warning(
                    "RPC rate limited ({}). Retrying in {:.1f}s (attempt {}/{})",
                    exc,
                    delay,
                    attempt,
                    self._max_retries,
                )
                time.sleep(delay)
                delay = min(delay * 2, 30.0)


def _is_rate_limit_error(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    if response is not None and getattr(response, "status_code", None) == 429:
        return True
    if requests is not None and isinstance(exc, requests.HTTPError):
        response = exc.response
        return response is not None and response.status_code == 429
    return "429" in str(exc)


def init_wallet(config: BotConfig) -> BotWallet:
    provider = RetryingHTTPProvider(config.poidh_rpc_url, max_retries=5, backoff_seconds=1.5)
    web3 = Web3(provider)
    if not web3.is_connected():
        raise WalletError("Failed to connect to RPC")

    # Some POIDH networks use PoA-style headers.
    if geth_poa_middleware is not None:
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    account = web3.eth.account.from_key(config.wallet_private_key)
    address = Web3.to_checksum_address(account.address)

    if config.wallet_address and Web3.to_checksum_address(config.wallet_address) != address:
        raise WalletError("WALLET_ADDRESS does not match WALLET_PRIVATE_KEY")

    return BotWallet(address=address, web3=web3)
