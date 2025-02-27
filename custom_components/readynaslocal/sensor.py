"""Sensors for ReadyNAS integration."""

import logging
import time
from datetime import timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry  # Add this import
from homeassistant.core import HomeAssistant  # Add this import
from homeassistant.helpers.entity import (
    DeviceInfo,
    EntityCategory,  # Add this import at the top
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN  # Add DOMAIN import
from .pyreadynas import ReadyNASAPI

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
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

    entities = []
    device_info = {
        "identifiers": {(DOMAIN, f"readynas_{host}")},
        "name": f"ReadyNAS ({host})",
        "manufacturer": "NETGEAR",
        "model": "ReadyNAS",
    }

    # Add basic sensors
    entities.append(
        ReadyNASSensor(coordinator, "cpu_temp", "CPU Temperature", "°C", device_info)
    )
    entities.append(
        ReadyNASSensor(
            coordinator=coordinator,
            sensor_key="fan_speed",
            name="Fan Speed",
            unit="RPM",  # Changed to RPM
            device_info=device_info,
        )
    )

    # Add disk sensors - one per disk with attributes
    for idx, disk in enumerate(coordinator.data.get("disks", [])):
        entities.append(
            ReadyNASDiskSensor(
                coordinator=coordinator, disk_index=idx, device_info=device_info
            )
        )

    # Add volume sensors
    for volume in coordinator.data.get("volumes", []):
        entities.append(
            ReadyNASVolumeSensor(
                coordinator=coordinator,
                volume_name=volume["name"],
                device_info=device_info,
            )
        )

    _LOGGER.info(f"🚀 Registering {len(entities)} sensors for {host}")
    async_add_entities(entities, True)


async def async_update_data(hass: HomeAssistant, entry: ConfigEntry, api: ReadyNASAPI):
    """Fetch data from API."""
    _LOGGER.debug(f"🚀 Starting update for ReadyNAS {entry.data['host']}")
    start_time = time.time()

    try:
        # Ensure API is using correct SSL settings from config entry
        api.use_ssl = entry.data.get("use_ssl", True)
        api.protocol = "https" if api.use_ssl else "http"
        api.url = f"{api.protocol}://{api.host}/dbbroker"
        api.admin_url = f"{api.protocol}://{api.host}/admin/"

        data = await api.get_health_info()
        if not data:
            _LOGGER.error("No data received from ReadyNAS API")
            raise UpdateFailed("Empty response from ReadyNAS")

        duration = time.time() - start_time
        _LOGGER.debug(
            f"✅ Update completed in {duration:.3f} seconds for {entry.data['host']}"
        )
        return data

    except Exception as err:
        duration = time.time() - start_time
        _LOGGER.error(f"❌ Update failed for {entry.data['host']}: {str(err)}")
        raise UpdateFailed(f"Failed to fetch ReadyNAS data: {str(err)}") from err


class ReadyNASDiskSensor(SensorEntity):
    """Representation of a ReadyNAS disk sensor with attributes."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, disk_index, device_info=None):
        """Initialize the disk sensor."""
        self.coordinator = coordinator
        self.disk_index = disk_index
        self._attr_name = f"Disk {disk_index + 1}"
        self._attr_unique_id = (
            f"readynas_{coordinator.config_entry.data['host']}_disk_{disk_index}"
        )
        self._attr_device_info = DeviceInfo(**device_info) if device_info else None
        self._attr_native_unit_of_measurement = None  # Remove unit for string state
        self._attr_device_class = None  # Disk status is a string
        self._attr_state_class = None  # Add this line
        self._attr_icon = "mdi:harddisk"  # Add this line

    @property
    def native_value(self):
        """Return the state of the disk."""
        if not self.coordinator.data or self.disk_index >= len(
            self.coordinator.data["disks"]
        ):
            return None
        return self.coordinator.data["disks"][self.disk_index]["status"]

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if not self.coordinator.data or self.disk_index >= len(
            self.coordinator.data["disks"]
        ):
            return {}

        disk_data = self.coordinator.data["disks"][self.disk_index]
        return {
            "temperature": disk_data.get("temperature"),
            "model": disk_data.get("model", "Unknown"),
            "capacity_gb": round(disk_data.get("capacity", 0) / 1e9, 2),
        }

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class ReadyNASSensor(SensorEntity):
    """Representation of a ReadyNAS sensor."""

    _attr_has_entity_name = True  # Add this line

    def __init__(self, coordinator, sensor_key, name, unit, device_info=None) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.sensor_key = sensor_key
        self.icon = "mdi:thermometer"  # Add this line for the icon
        self._attr_name = name  # Just use the name without prefix
        self._attr_unique_id = (
            f"readynas_{self.coordinator.config_entry.data['host']}_{sensor_key}"
        )
        self._attr_device_info = DeviceInfo(**device_info) if device_info else None
        self._attr_native_unit_of_measurement = unit if unit else None

        # ✅ Assign correct `device_class` based on sensor key
        if "temperature" in sensor_key:
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = "°C"
            self._attr_icon = "mdi:thermometer"  # Add this line for the icon
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif "fan_speed" in sensor_key:
            self._attr_device_class = None  # Fan speed is a number
            self._attr_native_unit_of_measurement = "RPM"
            self._attr_icon = "mdi:fan"  # Add this line for the icon
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif "capacity" in sensor_key or "used" in sensor_key or "free" in sensor_key:
            self._attr_device_class = SensorDeviceClass.DATA_SIZE
            self._attr_native_unit_of_measurement = "GB"
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif "health" in sensor_key or "status" in sensor_key:
            self._attr_device_class = None  # Status/health is a string
        elif "model" in sensor_key or "model" in sensor_key:
            self._attr_device_class = None  # Status/health is a string

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def native_value(self):
        """Return the sensor value."""
        if not self.coordinator.data:
            _LOGGER.warning("⚠️ Warning: No data available for {self._attr_name}")
            return None

        # ✅ Handle disk sensors separately
        if self.sensor_key.startswith("disk_"):
            parts = self.sensor_key.split("_")
            disk_index = int(parts[1])
            disk_param = parts[2]

            if disk_index < len(self.coordinator.data["disks"]):
                disk_data = self.coordinator.data["disks"][disk_index]

                if disk_param in disk_data:
                    if disk_param == "capacity":
                        return round(
                            disk_data[disk_param] / 1e9, 2
                        )  # Convert bytes to GB
                    return disk_data[disk_param]
                else:
                    _LOGGER.warning(
                        "⚠️ Warning: Missing key `{disk_param}` in disk data! Available keys: {disk_data.keys()}"
                    )
                    return None

        # ✅ Handle volume sensors
        if self.sensor_key.startswith("volume_"):
            parts = self.sensor_key.split("_")
            volume_name = parts[1]
            volume_param = parts[2]

            for volume in self.coordinator.data.get("volumes", []):
                if volume["name"] == volume_name and volume_param in volume:
                    if volume_param in ["used", "free"]:
                        return round(
                            volume[volume_param] / 1e9, 2
                        )  # Convert bytes to GB
                    return volume[volume_param]

            _LOGGER.warning(
                "⚠️ Warning: Volume `{volume_name}` does not have key `{volume_param}`."
            )
            return None

        # ✅ Handle standard sensors
        if self.sensor_key not in self.coordinator.data:
            _LOGGER.warning(
                "⚠️ Warning: Key `{self.sensor_key}` not found in API response! Available keys: {self.coordinator.data.keys()}"
            )
            return None

        _LOGGER.info(
            "✅ Sensor `{self.sensor_key}` updated: {self.coordinator.data[self.sensor_key]}"
        )
        return self.coordinator.data[self.sensor_key]

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class ReadyNASVolumeSensor(SensorEntity):
    """Representation of a ReadyNAS volume sensor."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC  # Changed from string to enum

    def __init__(self, coordinator, volume_name, device_info=None):
        """Initialize the volume sensor."""
        self.coordinator = coordinator
        self._volume_name = volume_name
        self._attr_name = f"Volume {volume_name}"
        self._attr_unique_id = (
            f"readynas_{coordinator.config_entry.data['host']}_volume_{volume_name}"
        )
        self._attr_device_info = DeviceInfo(**device_info) if device_info else None
        self._attr_native_unit_of_measurement = None  # Changed to valid data size unit
        self._attr_device_class = None
        self._attr_icon = "mdi:nas"  # Add this line for the icon

    @property
    def native_value(self):
        """Return the state of the volume."""
        if not self.coordinator.data or "volumes" not in self.coordinator.data:
            return None

        # Find the volume by name and return size in GiB
        for volume in self.coordinator.data["volumes"]:
            if volume["name"] == self._volume_name:
                return volume[
                    "health"
                ]  # round(volume["capacity_gb"], 2)  # Return capacity in GiB
        return None

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if not self.coordinator.data or "volumes" not in self.coordinator.data:
            return {}

        for volume in self.coordinator.data["volumes"]:
            if volume["name"] == self._volume_name:
                return {
                    "capacity_gb": round(volume["capacity_gb"], 2),
                    "free_gb": round(volume["free_gb"], 2),
                    "used_gb": round(volume["used_gb"], 2),
                    "used_percentage": round(volume["used_percentage"], 1),
                    "raid_level": volume["raid_level"],
                    "encryption_enabled": volume["encryption_enabled"],
                    "auto_expand": volume["auto_expand"],
                    "quota_enabled": volume["quota_enabled"],
                    "raid_configs": volume["raid_configs"],
                }
        return {}

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
