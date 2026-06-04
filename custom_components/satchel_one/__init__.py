"""The Satchel One integration."""

from __future__ import annotations

import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .api.client import SatchelOneClient
from .coordinator import BehaviourCoordinator, HomeworkCoordinator
from .const import DOMAIN, MIN_UPDATE_INTERVAL

PLATFORMS = ["sensor", "binary_sensor"]


def _linked_person(entry: ConfigEntry, child_id: int) -> str | None:
    child_person_map = entry.options.get("child_person_map", {})
    value = child_person_map.get(str(child_id))
    return value if value and value != "none" else None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Satchel One from a config entry."""
    session = aiohttp_client.async_get_clientsession(hass)
    client = SatchelOneClient(session=session, token=entry.data["token"])

    min_mins = MIN_UPDATE_INTERVAL // 60
    hw_mins = max(entry.options.get("homework_interval_minutes", 30), min_mins)
    beh_mins = max(entry.options.get("behaviour_interval_minutes", 15), min_mins)
    hw_interval = datetime.timedelta(minutes=hw_mins)
    beh_interval = datetime.timedelta(minutes=beh_mins)

    hw_coordinators: dict[int, HomeworkCoordinator] = {}
    beh_coordinators: dict[int, BehaviourCoordinator] = {}

    for child in entry.data["children"]:
        cid = child["id"]
        cname = child["name"]
        person = _linked_person(entry, cid)

        hw_coord = HomeworkCoordinator(
            hass=hass, client=client, student_id=cid,
            child_name=cname, linked_person=person,
            update_interval=hw_interval,
        )
        beh_coord = BehaviourCoordinator(
            hass=hass, client=client, student_id=cid,
            child_name=cname, linked_person=person,
            update_interval=beh_interval,
        )
        await hw_coord.async_refresh()
        await beh_coord.async_refresh()

        hw_coordinators[cid] = hw_coord
        beh_coordinators[cid] = beh_coord

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "homework": hw_coordinators,
        "behaviour": beh_coordinators,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
