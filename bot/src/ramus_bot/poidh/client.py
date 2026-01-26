from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from web3 import Web3
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import BotConfig
from ..models import BountySpec, Claim
from ..wallet import BotWallet
from .contracts import POIDH_CHAIN_CONFIG, POIDH_MINIMAL_ABI


@dataclass(frozen=True)
class PoidhClient:
    wallet: BotWallet
    config: BotConfig

    def _contract(self):
        chain = POIDH_CHAIN_CONFIG.get(self.config.poidh_chain_slug)
        if not chain:
            raise ValueError(f"Unsupported chain slug: {self.config.poidh_chain_slug}")
        address = Web3.to_checksum_address(chain["main_contract"])
        return self.wallet.web3.eth.contract(address=address, abi=POIDH_MINIMAL_ABI)

    def _send_tx(self, txn):
        signed = self.wallet.web3.eth.account.sign_transaction(
            txn, private_key=self.config.wallet_private_key
        )
        raw_tx = getattr(signed, "rawTransaction", None)
        if raw_tx is None:
            raw_tx = getattr(signed, "raw_transaction", None)
        if raw_tx is None:
            raise AttributeError("Signed transaction missing raw transaction bytes.")
        tx_hash = self.wallet.web3.eth.send_raw_transaction(raw_tx)
        receipt = self.wallet.web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), reraise=True)
    def create_bounty(self, spec: BountySpec) -> int:
        contract = self._contract()
        nonce = self.wallet.web3.eth.get_transaction_count(self.wallet.address)
        if spec.bounty_type == "open":
            fn = contract.functions.createOpenBounty(spec.title, spec.description)
        else:
            fn = contract.functions.createSoloBounty(spec.title, spec.description)

        txn = fn.build_transaction(
            {
                "from": self.wallet.address,
                "nonce": nonce,
                "value": spec.reward_wei,
                "chainId": self.config.poidh_chain_id,
            }
        )
        self._send_tx(txn)
        bounty_id = contract.functions.bountyCounter().call()
        return int(bounty_id)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), reraise=True)
    def fetch_claims(self, bounty_id: int) -> list[Claim]:
        contract = self._contract()
        claims: list[Claim] = []
        offset = 0
        while True:
            chunk = contract.functions.getClaimsByBountyId(bounty_id, offset).call()
            if not chunk:
                break
            for raw in chunk:
                claims.append(self._parse_claim(raw))
            offset += len(chunk)
        return claims

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), reraise=True)
    def accept_claim(self, bounty_id: int, claim_id: int) -> str:
        contract = self._contract()
        nonce = self.wallet.web3.eth.get_transaction_count(self.wallet.address)
        txn = contract.functions.acceptClaim(bounty_id, claim_id).build_transaction(
            {
                "from": self.wallet.address,
                "nonce": nonce,
                "chainId": self.config.poidh_chain_id,
            }
        )
        receipt = self._send_tx(txn)
        return receipt.transactionHash.hex()

    @staticmethod
    def _parse_claim(raw: Iterable) -> Claim:
        return Claim(
            claim_id=int(raw[0]),
            issuer=Web3.to_checksum_address(raw[1]),
            bounty_id=int(raw[2]),
            bounty_issuer=Web3.to_checksum_address(raw[3]),
            title=str(raw[4]),
            description=str(raw[5]),
            created_at=datetime.utcfromtimestamp(int(raw[6])),
            accepted=bool(raw[7]),
        )
