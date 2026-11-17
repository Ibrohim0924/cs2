from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import router
from app.core.database import Base, get_db
from app.seed import seed_data


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
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
