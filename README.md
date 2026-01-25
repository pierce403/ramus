# Ramus

Ramus is an ancient tree god that runs autonomous POIDH bounties. The system includes:

- **Python bot**: creates bounties, monitors submissions, selects winners, and pays out.
- **Web app**: static React site at `ramus.ai` with XMTP chat to the bot.

## Repository layout

```
bot/   Python XMTP bot + POIDH runner
web/   React + TypeScript static site
docs/  Research notes, decisions, bounty run logs
scripts/  Utility scripts
```

## Requirements

- Python 3.11+
- Node.js 20+
- Funded wallet for POIDH bounties (Base/Arbitrum/Degen)

## Bot setup

```bash
cd bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env
# Fill in wallet key + XMTP settings (Base RPC defaults to https://mainnet.base.org)

python -m ramus_bot
```

### Key env vars (bot)

See `bot/.env.example` and `docs/secrets.md`.

## Web setup

```bash
cd web
npm install
cp .env.example .env
npm run dev
```

### XMTP browser chat

The web app uses `@xmtp/browser-sdk` with a wallet-based signer. You must set:

- `VITE_XMTP_ENV`
- `VITE_XMTP_BOT_ADDRESS`

## Deployment

- GitHub Actions deploys `web/` to GitHub Pages.
- Custom domain: `ramus.ai`.

## Architecture & docs

- Architecture: `ARCHITECTURE.md`
- POIDH notes: `docs/poidh.md`
- XMTP notes + protocol: `docs/xmtp.md`
- Selection rubric: `docs/selection.md`
- Safety rails: `docs/safety.md`

## Demo bounty run

To claim the POIDH bounty, run at least one real bounty end-to-end and record proof:

- Use the bot to create a bounty.
- Wait for submissions from real participants.
- Let the bot select a winner and pay out.
- Record tx hash + screenshots + links.

Use `docs/bounty-runs/template.md` to document the run.

## License

Apache 2.0 (see `LICENSE`).
