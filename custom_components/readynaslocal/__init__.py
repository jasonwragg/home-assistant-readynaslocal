"""Module for ReadyNAS integration with Home Assistant."""

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .pyreadynas import ReadyNASAPI

PLATFORMS = [Platform.BUTTON, Platform.SENSOR]


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
    hass.data[DOMAIN][entry.entry_id] = api

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

    return unload_ok


class ReadyNASShutdownButton(ButtonEntity):
    """Representation of ReadyNAS shutdown button."""

    def __init__(self, api, name) -> None:
        """Initialize the button."""
        self._api = api
        self._attr_name = f"{name} Shutdown"
        self._attr_unique_id = f"{name.lower()}_shutdown"
        self._attr_entity_category = EntityCategory.CONFIG

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._api.shutdown_nas()
