"""Select entities for ReadyNAS integration."""

import logging
from datetime import timedelta

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up ReadyNAS sensors."""
    api = hass.data[DOMAIN][entry.entry_id]
    host = entry.data["host"]

    # Create coordinator with same SSL settings as initial setup
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"ReadyNAS {host}",
        update_method=lambda: async_update_data(hass, entry, api),
        update_interval=timedelta(seconds=30),
    )

    await coordinator.async_config_entry_first_refresh()
    device_info = {
        "identifiers": {(DOMAIN, f"readynas_{host}")},
        "name": f"ReadyNAS ({host})",
        "manufacturer": "NETGEAR",
        "model": "ReadyNAS",
    }
    async_add_entities([ReadyNASFanMode(coordinator, entry, api, device_info)], True)


async def async_update_data(hass: HomeAssistant, entry: ConfigEntry, api):
    """Fetch data from API."""
    try:
        # Ensure API is using correct SSL settings from config entry
        api.use_ssl = entry.data.get("use_ssl", True)
        api.protocol = "https" if api.use_ssl else "http"
        api.url = f"{api.protocol}://{api.host}/dbbroker"
        api.admin_url = f"{api.protocol}://{api.host}/admin/"

        fan_mode = await api.get_fan_mode()
        return {"fan_mode": fan_mode}
    except Exception as err:
        _LOGGER.error("Error updating ReadyNAS data: %s", err)
        return None


class ReadyNASFanMode(CoordinatorEntity, SelectEntity):
    """Select entity for fan mode control."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = ["cool", "balanced", "quiet"]
    _attr_has_entity_name = True

    def __init__(self, coordinator, config_entry, api, device_info=None):
        """Initialize the fan mode select."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._api = api
        self._attr_unique_id = f"{config_entry.entry_id}_fan_mode"
        self._attr_name = "Fan Mode"
        self._attr_device_info = DeviceInfo(**device_info) if device_info else None

    @property
    def current_option(self) -> str | None:
        """Return the current fan mode."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("fan_mode")

    async def async_select_option(self, option: str) -> None:
        """Change the fan mode."""
        await self._api.set_fan_mode(option)
        await self.coordinator.async_request_refresh()
