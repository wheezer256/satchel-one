"""Binary sensor entities for Satchel One."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .sensor import _linked_person

if TYPE_CHECKING:
    from .coordinator import BehaviourCoordinator, HomeworkCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Satchel One binary sensors from a config entry."""
    coordinators: dict = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for child in entry.data["children"]:
        hw_coord = coordinators["homework"][child["id"]]
        beh_coord = coordinators["behaviour"][child["id"]]
        cid, cname = child["id"], child["name"]
        entities += [
            OverdueHomeworkBinarySensor(hw_coord, cid, cname, entry),
            DetentionTodayBinarySensor(beh_coord, cid, cname, entry),
        ]
    async_add_entities(entities)


class _ChildBinarySensorBase(BinarySensorEntity):
    """Common base for per-child binary sensors."""

    def __init__(
        self,
        coordinator,
        child_id: int,
        child_name: str,
        entry: ConfigEntry | None = None,
    ) -> None:
        self._coordinator = coordinator
        self._child_id = child_id
        self._child_name = child_name
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._child_id)},
            name=self._child_name,
            manufacturer="Satchel One",
        )


class OverdueHomeworkBinarySensor(_ChildBinarySensorBase):
    """On when any incomplete task is past its due date."""

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_{self._child_id}_overdue_homework"

    @property
    def name(self) -> str:
        return f"{self._child_name} Overdue Homework"

    @property
    def is_on(self) -> bool:
        if not self._coordinator.data:
            return False
        today = date.today()
        for hw in self._coordinator.data["homework"]:
            if hw.completed:
                continue
            try:
                due = date.fromisoformat(hw.due_on[:10])
            except (ValueError, TypeError):
                continue
            if due < today:
                return True
        return False


class DetentionTodayBinarySensor(_ChildBinarySensorBase):
    """On when a detention is scheduled for today."""

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_{self._child_id}_detention_today"

    @property
    def name(self) -> str:
        return f"{self._child_name} Detention Today"

    @property
    def is_on(self) -> bool:
        if not self._coordinator.data:
            return False
        today = date.today()
        for d in self._coordinator.data["detentions"]:
            if not d.scheduled_at:
                continue
            try:
                detention_date = date.fromisoformat(d.scheduled_at[:10])
            except (ValueError, TypeError):
                continue
            if detention_date == today:
                return True
        return False
