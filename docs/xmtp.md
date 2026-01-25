# XMTP Notes

## Python bot (xmtp-py)

- Use the xmtp-py agent SDK for event-driven messaging.
- The bot listens for `text` messages and responds with status or bounty commands.

## Message protocol

Ramus expects either plain text commands (`status`, `help`) or JSON:

```json
{"action": "bounty.create", "payload": {"title": "...", "description": "...", "reward_wei": 0}}
```

## Key environment variables

- `XMTP_ENV` (production or dev)
- `XMTP_DB_PATH`
- `XMTP_WALLET_KEY`

## Browser SDK

The web app will use the XMTP browser SDK to open a DM with the bot and send command messages.
