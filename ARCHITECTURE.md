# Architecture Overview

This is a living document. Update it as the codebase evolves.

## 1. Project Structure

Planned layout (update as it becomes real):

```
[Project Root]/
├── bot/              # Python XMTP bot and POIDH bounty runner
├── web/              # React + TypeScript static site (ramus.ai)
├── docs/             # Architecture notes, bounty run reports, decisions
├── scripts/          # Automation utilities
├── AGENTS.md         # Agent guidance and learnings
├── ARCHITECTURE.md   # This file
└── README.md         # Human-facing overview and setup
```

## 2. High-Level System Diagram

```
[User] <-> [Web App (ramus.ai)] <-> [XMTP Network] <-> [Ramus Bot]
                                                         |
                                                         +-> [POIDH API / On-chain]
                                                         |
                                                         +-> [State Store]
```

## 3. Core Components

### 3.1. Web App

Name: Ramus Web

Description: Static site for onboarding, bounty guidance, and a chat interface to Ramus via XMTP.

Technologies: React, TypeScript, XMTP browser SDK

Deployment: Static hosting (provider TBD)

### 3.2. Ramus Bot

Name: Ramus Bot

Description: Python service that creates POIDH bounties, monitors submissions, selects a winner, and pays out.

Technologies: Python, xmtp-py, POIDH API/client, wallet tooling

Deployment: Long-running service (VPS or container; TBD)

### 3.3. Decision Engine

Name: Submission Evaluator

Description: Scores submissions against a deterministic rubric; may use AI assistance for evidence checks while keeping a clear explanation.

Technologies: Python (optional LLM provider; TBD)

Deployment: Runs inside the bot process

## 4. Data Stores

### 4.1. Bounty State Store

Name: Bot State Store

Type: TBD (SQLite or hosted DB)

Purpose: Track bounty metadata, submissions, evaluation results, and payouts.

Key Tables: bounties, submissions, evaluations, payouts

## 5. External Integrations / APIs

- POIDH: bounty creation, submission retrieval, payouts.
- XMTP: bot messaging and web chat.
- Blockchain RPC provider: transaction submission and lookup.

## 6. Deployment & Infrastructure

Cloud Provider: TBD

Key Services: static hosting for web, VPS/container for bot, secrets manager for keys

CI/CD: TBD

Monitoring & Logging: structured logs; alerts for payout failures

## 7. Security Considerations

- Protect bot private keys (env vars or secrets manager).
- Validate submission proofs and avoid automatic payout on insufficient evidence.
- Log decisions and rationale for auditability.
- Rate limit external API calls and handle retries safely.

## 8. Development & Testing Environment

Local Setup: documented in README.

Testing Frameworks: TBD (likely pytest for Python, vitest/jest for web).

Code Quality Tools: TBD (likely ruff/black for Python, eslint/prettier for web).

## 9. Future Considerations / Roadmap

- Farcaster posting integration.
- More robust proof validation (metadata checks, reverse image search, etc.).
- Public status API for live bounty dashboards.

## 10. Project Identification

Project Name: Ramus

Repository URL: TBD

Primary Contact/Team: TBD

Date of Last Update: 2026-01-25

## 11. Glossary / Acronyms

- XMTP: Extensible Message Transport Protocol
- POIDH: Proof-of-Impact bounty platform (poidh.xyz)
- IRL: In real life
