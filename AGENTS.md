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
# Add verified commands here
```

## Coding Conventions

- Document any style or naming conventions as they emerge.
- Keep persona text and message templates centralized for reuse.

## Known Issues & Solutions

- None yet. Add problems encountered and fixes here.

## Dependencies

- Python: xmtp-py, POIDH client/API, wallet tooling
- Web: React + TypeScript, XMTP browser SDK
- Add versions when confirmed.

## Deployment Notes

- Web: static hosting for ramus.ai (provider TBD).
- Bot: long-running service with wallet access and durable state.

## Agent Tips

- The bot must be fully autonomous and explain winner selection.
- POIDH bounties must involve real-world actions with proof.
- Avoid assumptions about POIDH/XMTP APIs; verify with docs.

## Rapport & Reflection

- Collaborator prefers concise, structured outputs and TODOs.
- Use clear, grounded language; avoid fluff.
- Keep this file short and updated as the codebase grows.

## How to Use This File

1. Read it at the start of each task.
2. Update it before you finish if you learned anything useful.
3. Be specific: commands, paths, decisions, and pitfalls.
