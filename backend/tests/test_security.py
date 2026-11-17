import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from fastapi import HTTPException

from app.core import security
from app.services.steam_provider import SteamDeliveryProvider


def signed_init_data(bot_token: str, *, auth_date: int | None = None) -> str:
    fields = {
        "auth_date": str(auth_date or int(time.time())),
        "query_id": "test-query",
        "user": json.dumps({"id": 12345, "first_name": "Test"}),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


def test_telegram_init_data_signature_is_verified(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security.settings, "telegram_bot_token", "test-token")
    assert security.validate_telegram_init_data(signed_init_data("test-token"))["id"] == 12345


def test_telegram_init_data_rejects_bad_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security.settings, "telegram_bot_token", "test-token")
    with pytest.raises(HTTPException) as error:
        security.validate_telegram_init_data(signed_init_data("other-token"))
    assert error.value.status_code == 401


def test_telegram_init_data_rejects_stale_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security.settings, "telegram_bot_token", "test-token")
    with pytest.raises(HTTPException) as error:
        security.validate_telegram_init_data(signed_init_data("test-token", auth_date=int(time.time()) - 86401))
    assert error.value.status_code == 401


def test_steam_delivery_stays_disabled_without_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security.settings, "steam_delivery_enabled", True)
    provider = SteamDeliveryProvider()
    assert provider.enabled is False
    with pytest.raises(RuntimeError, match="disabled"):
        provider.request_delivery(trade_url="https://example.invalid", asset_id="asset")
