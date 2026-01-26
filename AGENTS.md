# AGENTS.md - Instructions for Coding Agents

## Self-Improvement Directive

IMPORTANT: Update this file whenever you learn something important about the project.
Capture both wins and misses. Include rapport-building observations about collaborators.
Add concrete commands, file paths, and examples.

## Project Overview

Ramus is an ancient tree god persona. The project will include:
- A Python bot using XMTP (xmtp-py) to run POIDH bounties end-to-end.
- A static TypeScript/React web app at ramus.ai using the XMTP browser SDK.
- A transparent, autonomous bounty runner with auditable reasoning.

## Project Structure

Planned layout (update as it becomes real):
- `bot/`     Python bot, XMTP integration, POIDH logic
- `web/`     React app (TypeScript), XMTP browser SDK
- `docs/`    Architecture notes, bounty runs, decisions
- `scripts/` Utilities for setup and deployment

## Build & Test Commands

```bash
# Web build
cd web && npm run build
```

## Coding Conventions

- Document any style or naming conventions as they emerge.
- Keep persona text and message templates centralized for reuse.

## Known Issues & Solutions

- ENS resolution can fail if `web3` doesn't auto-load the ENS helper. Use `ENS.from_web3` when `w3.ens` is missing. Updated in `bot/src/ramus_bot/xmtp_bot.py`.
- XMTP sender addresses may arrive as non-string types; coerce to string/hex before comparison in `bot/src/ramus_bot/xmtp_bot.py`.
- Ethers v6 `Wallet.createRandom()` returns `HDNodeWallet` (private fields) and is not assignable to `Wallet`; avoid typing the helper as `Wallet` in `web/src/components/ChatPanel.tsx`.
- `OPERATOR_ENS` is preferred when set; `OPERATOR_ADDRESS` is only used if ENS is blank or fails to resolve. See `bot/src/ramus_bot/xmtp_bot.py`.

## Dependencies

- Python: xmtp-py, POIDH client/API, wallet tooling
- Web: React + TypeScript, XMTP browser SDK (>=6.1.2 to avoid unsupported libxmtp errors)
- Add versions when confirmed.

## Deployment Notes

- Web: static hosting for ramus.ai (provider TBD).
- Bot: long-running service with wallet access and durable state.

## Agent Tips

- The bot must be fully autonomous and explain winner selection.
- POIDH bounties must involve real-world actions with proof.
- Avoid assumptions about POIDH/XMTP APIs; verify with docs.
- Operator is expected to be `deanpierce.eth` (set `OPERATOR_ENS` or `OPERATOR_ADDRESS` accordingly).
- Runtime toggles (`AUTO_RUN`, bounty reward) are shared via `bot/src/ramus_bot/runtime.py` and can be updated over XMTP.
- If no bounty reward is set, the bot uses ~10% of the wallet balance as the default reward (auto-run + admin defaults).
- XMTP responses now emit stdout markers when processing/sent (`bot/src/ramus_bot/xmtp_bot.py`).
- Web3 SignedTransaction uses `raw_transaction` in newer versions; `bot/src/ramus_bot/poidh/client.py` now handles both `rawTransaction` and `raw_transaction`.
- Base RPC rate limits (429) trigger a shared cooldown (10m, 20m, 40m, ...) in `bot/src/ramus_bot/wallet.py`, so all threads pause before retrying. Warnings include high-level context (e.g., creating bounty, fetching claims) via `rpc_context`.
- `INFURA_API_KEY` is required for Base mainnet only; XMTP command `set infura_key <key>` updates env + RPC URLs (restart required). Public Base RPC is blocked.
- Help text now lists commands without "admin text" and ends with an "Operator only" line; persona only applies to non-command freeform when Venice is set.
- Bounty creation is guarded by a shared lock via `StateStore.bounty_creation_guard()` to prevent multiple open/creating bounties.
- `status` output includes wallet balance and environment config status (non-secret flags) via `bot/src/ramus_bot/xmtp_bot.py`.
- On RPC 429s the bot enters a global cooldown and fails fast (no sleeping); callers get a RateLimitError message from `bot/src/ramus_bot/wallet.py`.
- Venice responses stream to stdout when available (see `_stream_venice` in `bot/src/ramus_bot/xmtp_bot.py`).

## Rapport & Reflection

- Collaborator prefers concise, structured outputs and TODOs.
- Use clear, grounded language; avoid fluff.
- Keep this file short and updated as the codebase grows.

## How to Use This File

1. Read it at the start of each task.
2. Update it before you finish if you learned anything useful.
3. Be specific: commands, paths, decisions, and pitfalls.

## Workflow

- Always commit and push after making changes (default to `origin/main`).
