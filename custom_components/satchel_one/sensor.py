"""Sensor entities for Satchel One."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

if TYPE_CHECKING:
    from .coordinator import BehaviourCoordinator, HomeworkCoordinator


def _linked_person(entry: ConfigEntry | None, child_id: int) -> Optional[str]:
    """Return the linked person entity_id for a child, or None."""
    if entry is None:
        return None
    child_person_map = entry.options.get("child_person_map", {})
    value = child_person_map.get(str(child_id))
    return value if value and value != "none" else None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Satchel One sensors from a config entry."""
    coordinators: dict = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for child in entry.data["children"]:
        hw_coord = coordinators["homework"][child["id"]]
        beh_coord = coordinators["behaviour"][child["id"]]
        cid, cname = child["id"], child["name"]
        entities += [
            HomeworkDueSensor(hw_coord, cid, cname, entry),
            NextHomeworkSensor(hw_coord, cid, cname, entry),
            CreditsSensor(beh_coord, cid, cname, entry),
            DemeritsSensor(beh_coord, cid, cname, entry),
            ConductNetSensor(beh_coord, cid, cname, entry),
            DetentionsSensor(beh_coord, cid, cname, entry),
        ]
    async_add_entities(entities)


class _ChildSensorBase(SensorEntity):
    """Common base for per-child sensors."""

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

    def _base_attrs(self) -> dict:
        return {"linked_person": _linked_person(self._entry, self._child_id)}


class HomeworkDueSensor(_ChildSensorBase):
    """Number of outstanding (incomplete) homework tasks."""

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_{self._child_id}_homework_due"

    @property
    def name(self) -> str:
        return f"{self._child_name} Homework Due"

    @property
    def native_value(self) -> Optional[int]:
        if not self._coordinator.data:
            return None
        return sum(1 for h in self._coordinator.data["homework"] if not h.completed)

    @property
    def extra_state_attributes(self) -> dict:
        if not self._coordinator.data:
            return {}
        outstanding = [h for h in self._coordinator.data["homework"] if not h.completed]
        return {
            **self._base_attrs(),
            "tasks": [
                {
                    "title": h.title,
                    "subject": h.subject,
                    "due_on": h.due_on,
                    "teacher_name": h.teacher_name,
                }
                for h in outstanding
            ],
        }


class NextHomeworkSensor(_ChildSensorBase):
    """ISO timestamp of the next due incomplete homework task."""

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_{self._child_id}_next_homework"

    @property
    def name(self) -> str:
        return f"{self._child_name} Next Homework"

    @property
    def native_value(self) -> Optional[str]:
        if not self._coordinator.data:
            return None
        outstanding = sorted(
            (h for h in self._coordinator.data["homework"] if not h.completed),
            key=lambda h: h.due_on,
        )
        if not outstanding:
            return None
        return outstanding[0].due_on


class CreditsSensor(_ChildSensorBase):
    """Running total of positive behaviour points."""

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_{self._child_id}_credits"

    @property
    def name(self) -> str:
        return f"{self._child_name} Credits"

    @property
    def native_value(self) -> Optional[int]:
        if not self._coordinator.data:
            return None
        return self._coordinator.data["summary"].total_positive_count

    @property
    def extra_state_attributes(self) -> dict:
        if not self._coordinator.data:
            return {}
        positive = [p for p in self._coordinator.data["praises"] if p.positive]
        return {
            **self._base_attrs(),
            "recent_events": [
                {"points": p.points, "reason": p.description, "happened_on": p.happened_on}
                for p in positive
            ],
        }


class DemeritsSensor(_ChildSensorBase):
    """Running total of negative behaviour points. None for positive-only schools."""

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_{self._child_id}_demerits"

    @property
    def name(self) -> str:
        return f"{self._child_name} Demerits"

    @property
    def native_value(self) -> Optional[int]:
        if not self._coordinator.data:
            return None
        summary = self._coordinator.data["summary"]
        negative = [p for p in self._coordinator.data["praises"] if not p.positive]
        if not negative and summary.total_negative_count == 0:
            return None
        return summary.total_negative_count

    @property
    def extra_state_attributes(self) -> dict:
        if not self._coordinator.data:
            return {}
        negative = [p for p in self._coordinator.data["praises"] if not p.positive]
        return {
            **self._base_attrs(),
            "recent_events": [
                {"points": p.points, "reason": p.description, "happened_on": p.happened_on}
                for p in negative
            ],
        }


class ConductNetSensor(_ChildSensorBase):
    """Net conduct score (credits minus demerits)."""

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_{self._child_id}_conduct_net"

    @property
    def name(self) -> str:
        return f"{self._child_name} Conduct Net"

    @property
    def native_value(self) -> Optional[int]:
        if not self._coordinator.data:
            return None
        return self._coordinator.data["summary"].total_net_count

    @property
    def extra_state_attributes(self) -> dict:
        if not self._coordinator.data:
            return {}
        s = self._coordinator.data["summary"]
        return {
            **self._base_attrs(),
            "week_positive": s.week_positive_count,
            "week_negative": s.week_negative_count,
            "month_positive": s.month_positive_count,
            "month_negative": s.month_negative_count,
        }


class DetentionsSensor(_ChildSensorBase):
    """Count of upcoming detentions."""

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_{self._child_id}_detentions"

    @property
    def name(self) -> str:
        return f"{self._child_name} Detentions"

    @property
    def native_value(self) -> Optional[int]:
        if not self._coordinator.data:
            return None
        return len(self._coordinator.data["detentions"])

    @property
    def extra_state_attributes(self) -> dict:
        if not self._coordinator.data:
            return {}
        return {
            **self._base_attrs(),
            "detentions": [
                {
                    "scheduled_at": d.scheduled_at,
                    "description": d.description,
                    "location": d.location,
                }
                for d in self._coordinator.data["detentions"]
            ],
        }
