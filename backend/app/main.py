from collections import defaultdict, deque
from time import monotonic

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import router
from app.core.config import settings
from app.core.database import SessionLocal
from app.seed import seed_data

app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

_requests: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    now = monotonic()
    client = request.client.host if request.client else "unknown"
    hits = _requests[client]
    while hits and hits[0] < now - 60:
        hits.popleft()
    if len(hits) >= settings.rate_limit_per_minute:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    hits.append(now)
    return await call_next(request)


@app.on_event("startup")
def startup() -> None:
    if settings.app_env == "production":
        if settings.secret_key == "development-only-replace-before-deploy" or len(settings.secret_key) < 32:
            raise RuntimeError("Set a SECRET_KEY of at least 32 characters before production startup")
        if not settings.telegram_bot_token:
            raise RuntimeError("Set TELEGRAM_BOT_TOKEN before production startup")
        if settings.admin_password == "change-this-before-use":
            raise RuntimeError("Set a non-default ADMIN_PASSWORD before production startup")
    with SessionLocal() as db:
        seed_data(db)


app.include_router(router)
