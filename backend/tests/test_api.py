from collections.abc import Generator
import hashlib
import hmac
import json
import time
from unittest.mock import Mock
from urllib.parse import urlencode

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import router
from app.core.config import Settings, settings
from app.core.database import Base, get_db
from app.seed import seed_data


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "admin_username", "admin")
    monkeypatch.setattr(settings, "admin_password", "change-this-before-use")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with testing_sessions() as db:
        seed_data(db)

    test_app = FastAPI()
    test_app.include_router(router)

    def override_db():
        with testing_sessions() as db:
            yield db

    test_app.dependency_overrides[get_db] = override_db
    with TestClient(test_app) as test_client:
        yield test_client
    engine.dispose()


def player_headers(client: TestClient, username: str = "test_player") -> dict[str, str]:
    response = client.post("/api/auth/demo", json={"username": username})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_case_grants_fixed_reward_only_once(client: TestClient) -> None:
    headers = player_headers(client)
    case = client.get("/api/cases", headers=headers).json()[0]
    assert case["published_reward_name"]
    opened = client.post(f"/api/cases/{case['slug']}/open", headers=headers)
    assert opened.status_code == 200
    assert opened.json()["reward"] == case["published_reward_name"]
    assert client.post(f"/api/cases/{case['slug']}/open", headers=headers).status_code == 409
    assert len(client.get("/api/inventory", headers=headers).json()) == 1
    unlocked = {item["slug"]: item["unlocked"] for item in client.get("/api/me", headers=headers).json()["achievements"]}
    assert unlocked["first-case"] is True
    assert unlocked["collector"] is False


def test_task_reward_is_server_validated_and_not_repeatable(client: TestClient) -> None:
    headers = player_headers(client, "task_player")
    claim = client.post("/api/tasks/daily-checkin/claim", headers=headers)
    assert claim.status_code == 200
    assert claim.json()["crystals"] == 10
    assert client.post("/api/tasks/daily-checkin/claim", headers=headers).status_code == 409
    social = client.post("/api/tasks/community/claim", headers=headers)
    assert social.status_code == 400
    assert client.get("/api/me", headers=headers).json()["crystals"] == 10


def test_steam_url_and_withdrawal_never_claim_delivery(client: TestClient) -> None:
    headers = player_headers(client, "steam_player")
    invalid = client.put(
        "/api/steam",
        headers=headers,
        json={"trade_url": "https://steamcommunity.com/tradeoffer/new/?partner=&token="},
    )
    assert invalid.status_code == 422
    trade_url = "https://steamcommunity.com/tradeoffer/new/?partner=12345&token=Abc123"
    assert client.put("/api/steam", headers=headers, json={"trade_url": trade_url}).status_code == 200
    assert client.get("/api/steam", headers=headers).json()["trade_url"] == trade_url

    case = client.get("/api/cases", headers=headers).json()[0]
    item = client.post(f"/api/cases/{case['slug']}/open", headers=headers).json()
    result = client.post(f"/api/withdrawals/{item['inventory_item_id']}", headers=headers)
    assert result.status_code == 200
    assert result.json()["status"] == "requested"
    assert result.json()["delivery_enabled"] is False
    assert client.get("/api/withdrawals", headers=headers).json()[0]["status"] == "requested"


def test_admin_role_is_required_for_admin_data(client: TestClient) -> None:
    user_headers = player_headers(client, "role_player")
    assert client.get("/api/admin/overview", headers=user_headers).status_code == 403
    login = client.post(
        "/api/auth/admin",
        json={"username": "admin", "password": "change-this-before-use"},
    )
    assert login.status_code == 200
    admin_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/admin/overview", headers=admin_headers).status_code == 200
    assert client.get("/api/admin/withdrawals", headers=admin_headers).status_code == 200


def test_frontend_origin_accepts_production_and_preview_domains() -> None:
    config = Settings(frontend_origin="http://localhost:5173, https://cs2.example.vercel.app/,https://cs2.example.com")
    assert config.cors_origins == [
        "http://localhost:5173",
        "https://cs2.example.vercel.app",
        "https://cs2.example.com",
    ]


@pytest.mark.parametrize(
    ("database_url", "expected"),
    [
        ("postgres://db.example/neon?sslmode=require",
         "postgresql+psycopg://db.example/neon?sslmode=require"),
        ("postgresql://db.example/neon?sslmode=require",
         "postgresql+psycopg://db.example/neon?sslmode=require"),
        ("postgresql+psycopg://db.example/neon?sslmode=require",
         "postgresql+psycopg://db.example/neon?sslmode=require"),
    ],
)
def test_database_url_uses_psycopg_driver(database_url: str, expected: str) -> None:
    assert Settings(database_url=database_url).database_url == expected


def test_health_checks_database_connectivity(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_reports_database_unavailable_without_leaking_details(client: TestClient) -> None:
    unavailable_db = Mock()
    unavailable_db.execute.side_effect = SQLAlchemyError("private connection details")
    client.app.dependency_overrides[get_db] = lambda: unavailable_db

    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}


def test_telegram_auth_endpoint_creates_a_player_session(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    bot_token = "test-bot-token"
    monkeypatch.setattr(settings, "telegram_bot_token", bot_token)
    fields = {
        "auth_date": str(int(time.time())),
        "query_id": "test-query",
        "user": json.dumps({"id": 12345, "first_name": "Test"}),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    response = client.post("/api/auth/telegram", json={"init_data": urlencode(fields)})
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    assert client.get("/api/me", headers={"Authorization": f"Bearer {access_token}"}).json()["telegram_id"] == 12345
