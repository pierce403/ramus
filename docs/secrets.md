# Secrets and Environment Strategy

## Local development

- Use `.env` files alongside each component:
  - `bot/.env`
  - `web/.env`
- Copy from the `.env.example` templates.
- Never commit real secrets.
- If `WALLET_PRIVATE_KEY` is blank, the bot generates a key and stores it at `WALLET_KEY_PATH`.
- XMTP uses the same wallet key; if `XMTP_WALLET_KEY` is set, it must match.

## Production

- Store secrets in a managed secrets store (provider TBD).
- Inject environment variables into the bot process at runtime.
- Use GitHub Actions secrets for build/deploy settings.

## Rotation & Safety

- Rotate private keys if they leak.
- Use least-privilege API keys when possible.
- Keep a separate wallet for dev/test.
- Treat `VENICE_API_KEY` like any other paid API key.
