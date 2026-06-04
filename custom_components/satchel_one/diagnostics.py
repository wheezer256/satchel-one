"""Diagnostics support for Satchel One.

Returns a redacted snapshot of the config entry and last coordinator data,
safe to share in bug reports (no tokens, no child PII).
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinators = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})

    hw_data: dict = {}
    beh_data: dict = {}

    hw_coords = coordinators.get("homework", {})
    beh_coords = coordinators.get("behaviour", {})

    for child_id, coord in hw_coords.items():
        if coord.data:
            hw_data[child_id] = {
                "homework_count": len(coord.data.get("homework", [])),
                "last_update_success": getattr(coord, "last_update_success", None),
            }

    for child_id, coord in beh_coords.items():
        if coord.data:
            beh_data[child_id] = {
                "praises_count": len(coord.data.get("praises", [])),
                "detentions_count": len(coord.data.get("detentions", [])),
                "last_update_success": getattr(coord, "last_update_success", None),
            }

    return {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "children": [
                {"id": c["id"], "name": c["name"]}
                for c in entry.data.get("children", [])
            ],
            # token and email deliberately omitted
        },
        "coordinators": {
            "homework": hw_data,
            "behaviour": beh_data,
        },
    }
