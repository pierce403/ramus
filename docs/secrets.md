# Secrets and Environment Strategy

## Local development

- Use `.env` files alongside each component:
  - `bot/.env`
  - `web/.env`
- Copy from the `.env.example` templates.
- Never commit real secrets.

## Production

- Store secrets in a managed secrets store (provider TBD).
- Inject environment variables into the bot process at runtime.
- Use GitHub Actions secrets for build/deploy settings.

## Rotation & Safety

- Rotate private keys if they leak.
- Use least-privilege API keys when possible.
- Keep a separate wallet for dev/test.
