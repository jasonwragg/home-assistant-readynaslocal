"""Button for ReadyNAS integration."""

from __future__ import annotations
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN  # Add DOMAIN import
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ReadyNAS button based on a config entry."""
    api = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([ReadyNASShutdownButton(api, entry)], True)


class ReadyNASShutdownButton(ButtonEntity):
    """Representation of ReadyNAS shutdown button."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, api, entry) -> None:
        """Initialize the button."""
        self._api = api
        self._attr_name = f"ReadyNAS {entry.data['host']} Shutdown"
        self._attr_unique_id = f"readynas_{entry.data['host']}_shutdown"
        self._attr_device_info = {
            "identifiers": {
                (DOMAIN, f"readynas_{entry.data['host']}")
            },  # Changed to match sensor format
            "name": f"ReadyNAS ({entry.data['host']})",
            "manufacturer": "NETGEAR",
            "model": "ReadyNAS",
        }

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._api.shutdown_nas()
