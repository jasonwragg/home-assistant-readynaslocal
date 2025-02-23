"""Binary sensors for ReadyNAS integration."""

import logging
from datetime import timedelta

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    """Set up ReadyNAS binary sensors."""
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
    async_add_entities([ReadyNASHealthSensor(coordinator, entry, device_info)], True)


async def async_update_data(hass: HomeAssistant, entry: ConfigEntry, api):
    """Fetch data from API."""
    try:
        # Ensure API is using correct SSL settings from config entry
        api.use_ssl = entry.data.get("use_ssl", True)
        api.protocol = "https" if api.use_ssl else "http"
        api.url = f"{api.protocol}://{api.host}/dbbroker"
        api.admin_url = f"{api.protocol}://{api.host}/admin/"

        # Get the health info
        health_info = await api.get_volume_info()
        _LOGGER.debug("Health info received: %s", health_info)  # Add debug logging

        if health_info and isinstance(health_info, list) and health_info:
            # Get the first volume's health status
            volume = health_info[0]  # Get first volume
            data = {"health": volume.get("health", "unknown")}
            _LOGGER.debug("Returning data: %s", data)  # Add debug logging
            return data

        _LOGGER.warning("No health info received from API")  # Add warning logging
        return None

    except Exception as err:
        _LOGGER.error("Error updating ReadyNAS data: %s", err)
        return None


class ReadyNASHealthSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for ReadyNAS health status."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator, config_entry, device_info):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{config_entry.entry_id}_health_status"
        self._attr_name = "Health Status"
        self._attr_device_info = DeviceInfo(**device_info) if device_info else None

    @property
    def is_on(self):
        """Return True if the health status is degraded."""
        if not self.coordinator.data:
            return None
        health_status = self.coordinator.data.get("health")
        # Return True if health status is anything other than REDUNDANT
        return health_status != "REDUNDANT" if health_status else None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}
        return {
            "health_status": self.coordinator.data.get("health", "unknown"),
        }
