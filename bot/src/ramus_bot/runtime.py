from __future__ import annotations

from dataclasses import dataclass, field
import threading


@dataclass(frozen=True)
class RuntimeSnapshot:
    auto_run: bool
    bounty_reward_wei: int
    bounty_reward_source: str


@dataclass
class RuntimeSettings:
    auto_run: bool
    bounty_reward_wei: int
    bounty_reward_source: str
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def snapshot(self) -> RuntimeSnapshot:
        with self._lock:
            return RuntimeSnapshot(
                auto_run=self.auto_run,
                bounty_reward_wei=self.bounty_reward_wei,
                bounty_reward_source=self.bounty_reward_source,
            )

    def update_auto_run(self, value: bool) -> None:
        with self._lock:
            self.auto_run = value

    def update_reward(self, reward_wei: int, source: str) -> None:
        with self._lock:
            self.bounty_reward_wei = reward_wei
            self.bounty_reward_source = source
