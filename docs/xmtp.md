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
- `XMTP_WALLET_KEY` (optional; must match `WALLET_PRIVATE_KEY`)
- `OPERATOR_ENS` (optional; leave blank to use direct address)
- `OPERATOR_ADDRESS` (operator address; defaults to deanpierce.eth resolved address)
- `ETH_MAINNET_RPC_URL` (used for ENS resolution when `OPERATOR_ENS` is set)

## Admin commands (operator only)

```json
{"action": "admin.set_venice_key", "payload": {"key": "VENICE_API_KEY"}}
{"action": "admin.set_venice_model", "payload": {"model": "llama-3.3-70b"}}
```

Plain text shortcuts:

```
set venice_key <VENICE_API_KEY>
set venice_model <llama-3.3-70b>
```

Admin commands write to the bot's `.env` file and take effect after a restart.

## Browser SDK

The web app will use the XMTP browser SDK to open a DM with the bot and send command messages.
