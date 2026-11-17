from app.core.config import settings


class SteamDeliveryProvider:
    """Adapter boundary for an authorized trading supplier; no success is simulated."""

    @property
    def configured(self) -> bool:
        return False

    @property
    def enabled(self) -> bool:
        return settings.steam_delivery_enabled and self.configured

    def request_delivery(self, *, trade_url: str, asset_id: str) -> str:
        if not self.enabled:
            raise RuntimeError("Steam delivery is disabled until an authorized provider is configured")
        raise NotImplementedError("Configure an authorized Steam trade provider before enabling delivery")


steam_delivery_provider = SteamDeliveryProvider()
