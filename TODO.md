# TODO

## Project setup
- [x] Decide repo layout (e.g., `bot/`, `web/`, `docs/`, `scripts/`).
- [x] Add tooling for Python (lint/format/test) and TS/React (lint/test/build).
- [x] Define secrets management + env var strategy for local + prod.
- [x] Create a `docs/` area for POIDH/XMTP notes and decisions.

## POIDH bounty runner (Python bot)
- [x] Review POIDH API/docs: bounty creation, submissions, judging, payouts, and any required attestations.
- [x] Choose and initialize the bot wallet; confirm chain/network and funding flow.
- [x] Build bot core loop: create bounty -> wait -> evaluate -> select -> pay.
- [x] Implement deterministic selection rubric with an optional AI assist (documented).
- [x] Add submission verification helpers (image/video checks, metadata capture, integrity checks).
- [ ] Store state (bounty IDs, submissions, decisions, payouts) in a durable store.
- [ ] Add audit log + reasoning report for each bounty run.
- [ ] Add safety rails: timeouts, retry logic, dispute handling, and manual override hooks.

## XMTP integration
- [ ] Implement XMTP messaging in the Python bot (inbox, outbound status updates).
- [ ] Define a message protocol between web UI and bot (commands, status, errors).
- [ ] Set up the XMTP browser SDK in the web app for user chat.

## Web app (ramus.ai)
- [ ] Scaffold TypeScript + React app.
- [ ] Design the Ramus persona voice and message templates.
- [ ] Build pages: Home, How it Works, Live Bounties, Submit Proof, Bot Chat.
- [ ] Add XMTP-based chat UI to talk to the bot.
- [ ] Provide bounty guidelines + proof requirements.

## Demo + bounty proof
- [ ] Run at least one real POIDH bounty end-to-end (not completed by you/close contacts).
- [ ] Capture proof of completion (links, screenshots, payout tx).
- [ ] Document the full run in README + `docs/`.

## README and open source requirements
- [ ] Write clear setup instructions (env, wallets, XMTP, POIDH).
- [ ] Document architecture, selection logic, and safety assumptions.
- [ ] Add license + contribution notes (if needed).
