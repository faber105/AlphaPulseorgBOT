# AlphaPulse

AlphaPulse is a Telegram bot with a Telegram Mini App for Pocket Option trading signals. It includes:

- aiogram 3 bot with `/start`, subscriptions, Telegram Stars payments, and admin-reviewed channel join requests.
- FastAPI backend on port `8080` with Telegram Mini App auth, JWT, signals, sessions, subscription, user, and admin APIs.
- PostgreSQL 16 schema and async SQLAlchemy models.
- Redis-backed candle storage, Celery agents, technical indicators, ML model loading/training, and signal publishing.
- React/Vite/Tailwind Mini App on port `3000`.

## Local Start

1. Check `.env`. It already contains the provided bot token, `ADMIN_TELEGRAM_ID`, project name, and generated local JWT/admin secrets.
2. Fill optional keys when needed: `EXCHANGERATE_API_KEY`, `CRYPTOBOT_API_TOKEN`, `CF_TUNNEL_TOKEN`.
3. Start the stack:

```bash
docker compose up --build
```

Services:

- API: `http://localhost:8080`
- Mini App: `http://localhost:3000`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

## Admin

The admin Telegram ID is configured as `ADMIN_TELEGRAM_ID`. API admin endpoints require:

```text
Authorization: Bearer <ADMIN_TOKEN from .env>
```

Because the Telegram bot token was shared in chat, rotate it in BotFather before production deployment and update `.env`.

