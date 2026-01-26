from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
import threading
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


_rpc_context = threading.local()


@contextmanager
def rpc_context(label: str):
    previous = getattr(_rpc_context, "label", None)
    _rpc_context.label = label
    try:
        yield
    finally:
        _rpc_context.label = previous


def _current_rpc_context() -> str | None:
    return getattr(_rpc_context, "label", None)


class RetryingHTTPProvider(HTTPProvider):
    def __init__(
        self,
        *args,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
        max_backoff_seconds: float = 30.0,
        rate_limit_base_seconds: float = 600.0,
        rate_limit_reset_seconds: float = 3600.0,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._max_backoff_seconds = max_backoff_seconds
        self._rate_limit_lock = threading.Lock()
        self._rate_limit_until = 0.0
        self._rate_limit_level = 0
        self._last_rate_limit_time = 0.0
        self._rate_limit_base_seconds = rate_limit_base_seconds
        self._rate_limit_reset_seconds = rate_limit_reset_seconds

    def make_request(self, method, params):  # type: ignore[override]
        for attempt in range(1, self._max_retries + 1):
            try:
                self._sleep_if_rate_limited(method, params)
                return super().make_request(method, params)
            except Exception as exc:
                if not _is_rate_limit_error(exc) or attempt >= self._max_retries:
                    raise
                delay, level, until = self._register_rate_limit()
                self._log_rate_limit(
                    method,
                    params,
                    exc,
                    delay,
                    level,
                    until,
                    attempt,
                    self._max_retries,
                )
                time.sleep(delay)

    def _sleep_if_rate_limited(self, method, params) -> None:
        with self._rate_limit_lock:
            now = time.time()
            wait_seconds = max(0.0, self._rate_limit_until - now)
            level = self._rate_limit_level
        if wait_seconds > 0:
            context = _describe_rpc_method(method)
            detail = f"{context} ({method})" if context else str(method)
            extra = _describe_rpc_params(method, params)
            endpoint = getattr(self, "endpoint_uri", None) or "RPC"
            op_context = _current_rpc_context()
            op_prefix = f"{op_context}: " if op_context else ""
            logger.warning(
                "RPC globally rate limited (level {}) before {}{}{} on {}. Waiting {:.1f}s",
                level,
                op_prefix,
                detail,
                f" [{extra}]" if extra else "",
                endpoint,
                wait_seconds,
            )
            time.sleep(wait_seconds)

    def _register_rate_limit(self) -> tuple[float, int, float]:
        now = time.time()
        with self._rate_limit_lock:
            if now - self._last_rate_limit_time > self._rate_limit_reset_seconds:
                self._rate_limit_level = 0
            self._last_rate_limit_time = now
            self._rate_limit_level += 1
            delay = self._rate_limit_base_seconds * (2 ** (self._rate_limit_level - 1))
            self._rate_limit_until = max(self._rate_limit_until, now + delay)
            return delay, self._rate_limit_level, self._rate_limit_until

    def _log_rate_limit(
        self,
        method,
        params,
        exc: Exception,
        delay: float,
        level: int,
        until: float,
        attempt: int,
        max_attempts: int,
    ) -> None:
        context = _describe_rpc_method(method)
        detail = f"{context} ({method})" if context else str(method)
        extra = _describe_rpc_params(method, params)
        endpoint = getattr(self, "endpoint_uri", None) or "RPC"
        op_context = _current_rpc_context()
        op_prefix = f"{op_context}: " if op_context else ""
        until_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(until))
        logger.warning(
            "RPC rate limited during {}{}{} on {} ({}). Backing off {:.0f}s (level {}, until {}) (attempt {}/{})",
            op_prefix,
            detail,
            f" [{extra}]" if extra else "",
            endpoint,
            exc,
            delay,
            level,
            until_iso,
            attempt,
            max_attempts,
        )


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
    provider = RetryingHTTPProvider(
        config.poidh_rpc_url,
        max_retries=5,
        backoff_seconds=1.5,
        max_backoff_seconds=30.0,
        rate_limit_base_seconds=600.0,
        rate_limit_reset_seconds=3600.0,
    )
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
