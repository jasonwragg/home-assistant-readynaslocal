"""Module for ReadyNAS integration with Home Assistant."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .pyreadynas import ReadyNASAPI

PLATFORMS = [Platform.BUTTON, Platform.BINARY_SENSOR, Platform.SELECT, Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up ReadyNAS from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create API instance with HTTPS by default
    api = ReadyNASAPI(
        entry.data["host"],
        entry.data["username"],
        entry.data["password"],
        use_ssl=entry.data.get("use_ssl", True),  # Changed default to True
        ignore_ssl_errors=entry.data.get("ignore_ssl_errors", True),
    )

    # Store the API instance using the correct domain
    # Store the API instance
    hass.data[DOMAIN][entry.entry_id] = api

    async def shutdown_service(service_call):
        """Handle the shutdown service call."""
        # Get the device ID from the target
        target = service_call.data.get("target", {})
        device_ids = target.get("device_id", [])

        if not device_ids:
            _LOGGER.error("No device_id provided in service call")
            return

        # Find the correct API instance for the targeted device
        for device_id in device_ids:
            for entry_id, entry_data in hass.data[DOMAIN].items():
                device_registry = dr.async_get(hass)
                device = device_registry.async_get(device_id)

                if device and entry_id in device.config_entries:
                    api = hass.data[DOMAIN][entry_id]["api"]
                    success = await api.shutdown_nas()
                    if not success:
                        _LOGGER.error("Failed to shutdown NAS")
                    return

            _LOGGER.error(f"Device {device_id} not found")

    hass.services.async_register(DOMAIN, "shutdown", shutdown_service)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload all platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Remove API instance using correct domain
        if DOMAIN in hass.data:
            hass.data[DOMAIN].pop(entry.entry_id, None)

    hass.services.async_remove(DOMAIN, "shutdown")

    return unload_ok


class ReadyNASShutdownButton(ButtonEntity):
    """Representation of ReadyNAS shutdown button."""

    def __init__(self, api, name) -> None:
        """Initialize the button."""
        self._api = api
        self._attr_name = f"{name} Shutdown"
        self._attr_unique_id = f"{name.lower()}_shutdown"
        self.icon = "mdi:power"
        self._attr_entity_category = EntityCategory.CONFIG

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._api.shutdown_nas()
