# XMTP Notes

## Python bot (xmtp-py)

- Use the xmtp-py agent SDK for event-driven messaging.
- The bot listens for `text` messages and responds with status or bounty commands.

## Message protocol

Ramus expects plain text commands (`status`, `help`) and natural language queries.

Natural language queries are supported for common status questions, for example:

```
How many claims have been submitted?
Are there any that look good?
What was wrong with submission #3?
```

Operator-only manual commands:

```
make bounty
select winner #3
```

Settings/status commands:

```
settings
status
```

## Key environment variables

- `XMTP_ENV` (production or dev)
- `XMTP_DB_PATH`
- `XMTP_WALLET_KEY` (optional; must match `WALLET_PRIVATE_KEY`)
- `OPERATOR_ENS` (optional; preferred if set)
- `OPERATOR_ADDRESS` (operator address; used if `OPERATOR_ENS` is blank or fails to resolve)
- `ETH_MAINNET_RPC_URL` (used for ENS resolution when `OPERATOR_ENS` is set)

Plain text shortcuts:

```
set venice_key <VENICE_API_KEY>
set venice_model <llama-3.3-70b>
set bounty_reward_eth <0.01>
set bounty_reward_wei <10000000000000000>
set auto_run on
```

Admin commands write to the bot's `.env` file. Reward and auto-run changes update the live runner; other config updates may require a restart.

If no bounty reward is configured, Ramus uses ~10% of the wallet balance as the default reward.

## Browser SDK

The web app will use the XMTP browser SDK to open a DM with the bot and send command messages.
