# CS2 OPEN CASE BOT

A Telegram Mini App starter for a CS2 skin collection platform. The development catalog uses **free cases with exact, published rewards**. Paid cases, randomized rewards, and gambling mechanics are not implemented. Catalog images and items are illustrative development data, not proof of ownership or Steam delivery.

## What is included

- React, TypeScript, Vite, Tailwind CSS, React Router, Lucide UI with mobile navigation and responsive pages.
- FastAPI, SQLAlchemy, PostgreSQL, Alembic migrations, Pydantic validation, and an aiogram 3 `/start` bot.
- Telegram `initData` HMAC validation, short-lived signed sessions, hashed admin passwords, role checks, audit entries, and API rate limiting.
- User profile, wallets and transaction ledger, fixed-reward cases, inventory, tasks, referrals, leaderboards, Steam settings, and withdrawal request history.
- Admin APIs for user status, cases, rewards, skins, tasks, inventory, referrals, wallet transactions, withdrawals, and audit logs.
- Steam provider adapter boundary. Delivery remains disabled by default; the app never fabricates a successful trade.
- Telegram Web Apps API initialization, development-only demo login, and a separate `/admin` sign-in surface.

## Quick start (Docker)

Requirements: Docker Compose v2.

1. Copy `.env.example` to `.env`. Set a long random `SECRET_KEY`, a unique `ADMIN_PASSWORD`, and your Telegram bot token/username. Keep `STEAM_DELIVERY_ENABLED=false` until an authorized delivery provider is implemented and reviewed.
2. Set `WEBAPP_URL` to the public HTTPS address where the Mini App will be hosted. Telegram requires HTTPS for production Mini Apps.
3. Start the API, PostgreSQL, and web application:

   ```powershell
   docker compose up --build
   ```

4. Open `http://localhost:8080`. The admin interface is at `/admin`; credentials are the configured `ADMIN_USERNAME` and `ADMIN_PASSWORD`. For Telegram polling, start the optional bot profile:

   ```powershell
   docker compose --profile telegram up --build
   ```

5. API health and interactive docs are at `http://localhost:8000/api/health` and `http://localhost:8000/docs`.

The Compose stack runs the Alembic migration before starting the API and seeds clearly marked catalog entries. The default local Postgres password is for development only.

## Deploying on Vercel

Use two Vercel projects connected to this repository so the static frontend and
FastAPI backend are built with their own runtimes:

- **Frontend project:** set Root Directory to the repository root (`.`), not
  `frontend/`. The npm manifests and build script are at the repository root;
  Vite itself uses `frontend/` as its source root. `vercel.json` explicitly
  selects Vite and publishes `frontend/dist`.
- **Backend project:** create a second Vercel project from the same repository
  and set Root Directory to `backend/`. Vercel finds the FastAPI application
  at `app/main.py`, installs `requirements.txt` from that root, and selects
  Python 3.12 from `.python-version` in that root.

For a free hobby deployment, use [Vercel Hobby](https://vercel.com/pricing) for
the HTTP API ([FastAPI deployment guide](https://vercel.com/docs/frameworks/backend/fastapi))
and a hosted PostgreSQL provider such as [Neon Free](https://neon.com/pricing).
Neon's free database can scale to zero after inactivity, so the first database
request may be slower. Vercel Functions are request-driven; the optional
long-running `backend/bot.py` polling process is not kept alive by this API
deployment and needs a separate worker host if you use it.

1. Deploy the backend first. In the new Vercel project select **Root Directory**
   `backend/` (do not use the frontend root `vercel.json` or `frontend/`).
   Add these backend environment variables in its Vercel Project Settings:
   `APP_ENV=production`, `DATABASE_URL`, `SECRET_KEY`, `TELEGRAM_BOT_TOKEN`,
   `ADMIN_PASSWORD`, `ADMIN_USERNAME`, and `FRONTEND_ORIGIN`. Use a hosted
   PostgreSQL database for `DATABASE_URL`; SQLite storage on a Vercel function
   is not persistent. Add `WEBAPP_URL` and `TELEGRAM_BOT_USERNAME` if the bot
   uses them. Set `FRONTEND_ORIGIN` to
   `https://cs2-khm3x42v6-ibo-fb74.vercel.app` (no trailing slash). Separate
   additional exact allowed origins with commas; do not use a wildcard.
   For Neon, use its pooled connection URL for serverless access and change the
   scheme to `postgresql+psycopg://` while retaining the host, credentials,
   database, and `sslmode=require` query parameter.
2. Before the backend handles requests, apply its database migrations using
   the same `DATABASE_URL`:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
   .\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
   ```

   Run this from the repository root in an environment where `DATABASE_URL`
   points to the hosted database. Keep that value private.
3. In the frontend Vercel project, keep **Root Directory** at the repository
   root (`.`) and add `VITE_API_BASE_URL` with the HTTPS origin Vercel generated
   for the backend project, without a trailing slash or `/api`. Vite embeds
   this value at build time, so redeploy the frontend after adding or changing it.
4. Verify the deployed backend by requesting its generated HTTPS origin plus
   `/api/health`; it should return JSON with `"status":"ok"`. Then open the
   Telegram Mini App. Player sessions are created only by
   `POST /api/auth/telegram` with Telegram's signed `initData`; authentication
   is not simulated in production.

The backend's `FRONTEND_ORIGIN` allowlist must include the exact production
frontend domain. Add a preview domain only if it is needed. The frontend calls
`POST /api/auth/telegram` at `VITE_API_BASE_URL`; if that URL is missing or points
to the frontend project, the app displays a specific configuration/connection
error. `frontend/.env.example` documents the local frontend API URL.

Do not commit `.env` or put server secrets in frontend variables.

The root `requirements.txt` includes `backend/requirements.txt`, keeping local
and Docker installs aligned with the backend's Vercel dependency manifest.

## Local development (without Docker)

1. Create a virtual environment and install Python dependencies:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env`. For a standalone local backend, change `DATABASE_URL` to `sqlite:///./cs2bot.db`. Keep `APP_ENV=development`. In this mode the API exposes a development-only demo login when Telegram init data is absent.
3. Create tables and start the API:

   ```powershell
   alembic -c backend/alembic.ini upgrade head
   uvicorn app.main:app --app-dir backend --reload
   ```

4. In another terminal, install frontend dependencies and run Vite:

   ```powershell
   npm install
   npm run dev
   ```

   Vite proxies `/api` to `http://localhost:8000`. The demo login is unavailable outside development.

## Configuration and integrations

| Variable | Purpose |
|---|---|
| `APP_ENV` | `development` enables the demo identity endpoint. Use `production` for deployed environments. |
| `SECRET_KEY` | Signs app/admin session tokens; use a random secret of at least 32 characters in production. |
| `DATABASE_URL` | SQLAlchemy URL; Compose configures PostgreSQL. |
| `TELEGRAM_BOT_TOKEN` | Server-only bot token used for signed `initData` verification and bot polling. |
| `TELEGRAM_BOT_USERNAME` | Used to construct referral deep links. |
| `WEBAPP_URL` | Public HTTPS Mini App URL used by the bot's `/start` button. |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Initial admin account credentials. Change the password before deployment. |
| `STEAM_DELIVERY_ENABLED` | Must remain false until a compliant supplier and provider implementation are configured. |

Telegram authentication rejects invalid signatures and `auth_date` older than 24 hours. Never place the bot token, admin password, or server signing key in frontend variables.

The Steam Trade URL endpoint accepts only HTTPS `steamcommunity.com/tradeoffer/new/` links with `partner` and `token` query parameters. It does not request Steam passwords, Guard codes, or session cookies. Withdrawal requests are recorded for review; status `delivered` can only be supplied by a future authorized provider integration. Delivery stays disabled even if the environment flag is accidentally enabled; the adapter reports unavailable until an authorized provider is implemented and reviewed.

Referral links are attributed at registration, but referral reward grants are intentionally not enabled; fraud checks need a production policy and signals before rewards can be safely introduced. Social tasks also remain unclaimable until a server-side verification mechanism is implemented. Weekly/monthly leaderboard points are computed from XP ledger entries over the corresponding period.

## Database and seed data

- `backend/app/models.py` defines users, profiles, wallets, wallet and XP ledgers, cases, rewards, skins, inventory, tasks, referrals, achievements, withdrawals, admins, and audit logs.
- Migrations are in `backend/alembic/versions/`. Apply with `alembic -c backend/alembic.ini upgrade head`.
- The sample items and case images are development catalog placeholders. They do not have authorized provider asset IDs and do not imply ownership or withdrawal eligibility.

## Tests and build

```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend\tests
npm install
npm run build
```

In production, terminate TLS at a trusted proxy, set restrictive origin and secrets, run the API behind a production ASGI server, and use a shared rate limiter for multiple API replicas. The included in-memory limiter is a single-process baseline, not a distributed abuse-control service.
