from __future__ import annotations

from dataclasses import dataclass
import random
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
    def __init__(
        self,
        *args,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
        max_backoff_seconds: float = 30.0,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._max_backoff_seconds = max_backoff_seconds

    def make_request(self, method, params):  # type: ignore[override]
        for attempt in range(1, self._max_retries + 1):
            try:
                return super().make_request(method, params)
            except Exception as exc:
                if not _is_rate_limit_error(exc) or attempt >= self._max_retries:
                    raise
                delay = min(self._backoff_seconds * (2 ** (attempt - 1)), self._max_backoff_seconds)
                jitter = random.uniform(0, delay * 0.25)
                context = _describe_rpc_method(method)
                detail = f"{context} ({method})" if context else str(method)
                extra = _describe_rpc_params(method, params)
                endpoint = getattr(self, "endpoint_uri", None) or "RPC"
                logger.warning(
                    "RPC rate limited during {}{} on {} ({}). Retrying in {:.1f}s (attempt {}/{})",
                    detail,
                    f" [{extra}]" if extra else "",
                    endpoint,
                    exc,
                    delay + jitter,
                    attempt,
                    self._max_retries,
                )
                time.sleep(delay + jitter)


def _is_rate_limit_error(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    if response is not None and getattr(response, "status_code", None) == 429:
        return True
    if requests is not None and isinstance(exc, requests.HTTPError):
        response = exc.response
        return response is not None and response.status_code == 429
    return "429" in str(exc)


def _describe_rpc_method(method: str) -> str:
    return {
        "eth_getBalance": "wallet balance lookup",
        "eth_call": "contract call",
        "eth_sendRawTransaction": "transaction broadcast",
        "eth_getTransactionCount": "nonce lookup",
        "eth_feeHistory": "fee history lookup",
        "eth_gasPrice": "gas price lookup",
        "eth_getBlockByNumber": "block lookup",
    }.get(method, "")


def _describe_rpc_params(method: str, params) -> str:
    if not params:
        return ""
    try:
        if method == "eth_call" and isinstance(params[0], dict):
            to = params[0].get("to")
            return f"to={to}" if to else ""
        if method == "eth_getBalance":
            return f"address={params[0]}"
        if method == "eth_sendRawTransaction":
            return "raw_tx"
    except Exception:
        return ""
    return ""


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
