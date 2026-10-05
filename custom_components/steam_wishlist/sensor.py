"""Sensors for the Steam Wishlists integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import WishlistConfigEntry
from .const import DOMAIN
from .coordinator import WishlistCoordinator

SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="total",
        name="Total",
        icon="mdi:heart",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="wishlists",
    ),
    SensorEntityDescription(
        key="net",
        name="Net",
        icon="mdi:delta",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="wishlists",
    ),
    SensorEntityDescription(
        key="net_7d",
        name="Net 7d",
        icon="mdi:calendar-week",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="wishlists",
    ),
    SensorEntityDescription(
        key="adds",
        name="Adds",
        icon="mdi:heart-plus",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="wishlists",
    ),
    SensorEntityDescription(
        key="deletes",
        name="Deletes",
        icon="mdi:heart-minus",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="wishlists",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WishlistConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        WishlistSensor(coordinator, entry, description) for description in SENSORS
    )


class WishlistSensor(CoordinatorEntity[WishlistCoordinator], SensorEntity):
    """A single wishlist statistic."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WishlistCoordinator,
        entry: WishlistConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Valve",
            model=f"App {coordinator.appid}",
            configuration_url=f"https://partner.steamgames.com/apps/landing/{coordinator.appid}",
        )

    @property
    def native_value(self) -> int | None:
        return (self.coordinator.data or {}).get(self.entity_description.key)

    @property
    def extra_state_attributes(self) -> dict | None:
        # Only the total carries the chart history, to keep the recorder small.
        if self.entity_description.key != "total":
            return None
        data = self.coordinator.data or {}
        return {"last_date": data.get("last_date"), "series": data.get("series", [])}
