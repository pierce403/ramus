# Wallet Setup

## Chain choice

Default chain: Base (chainId 8453).

Rationale: lower fees and matches POIDH deployment in the app bundle.

## Funding flow

1. Create a dedicated bot wallet.
2. Fund with a small amount of native gas token (ETH on Base).
3. Deposit bounty reward amount when creating the bounty (contract is payable).
4. Keep a buffer for gas and retries.

## Environment variables

See `bot/.env.example` for required values.

## Safety

- Use separate wallets for dev and production.
- Rotate keys if compromised.
- Avoid storing keys in the repository.
