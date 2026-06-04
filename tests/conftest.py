"""Pytest configuration — stubs Home Assistant modules so models/client/coordinator
tests run without a full HA install."""

import sys
import types
import logging
import datetime


def _make_stub(*parts: str) -> None:
    """Register an empty module stub for the given dotted path."""
    path = ""
    for part in parts:
        path = f"{path}.{part}" if path else part
        if path not in sys.modules:
            sys.modules[path] = types.ModuleType(path)


# ── Core HA modules ────────────────────────────────────────────────────────
_make_stub("homeassistant")
_make_stub("homeassistant", "config_entries")
_make_stub("homeassistant", "core")
_make_stub("homeassistant", "helpers")
_make_stub("homeassistant", "helpers", "aiohttp_client")
_make_stub("homeassistant", "helpers", "update_coordinator")
_make_stub("homeassistant", "helpers", "entity")
_make_stub("homeassistant", "helpers", "entity_platform")
_make_stub("homeassistant", "helpers", "entity_registry")
_make_stub("homeassistant", "helpers", "selector")
_make_stub("homeassistant", "components")
_make_stub("homeassistant", "components", "sensor")
_make_stub("homeassistant", "components", "binary_sensor")
_make_stub("homeassistant", "helpers", "device_registry")
_make_stub("homeassistant", "const")
_make_stub("homeassistant", "exceptions")

ha      = sys.modules["homeassistant"]
ha_ce   = sys.modules["homeassistant.config_entries"]
ha_core = sys.modules["homeassistant.core"]
ha_uc   = sys.modules["homeassistant.helpers.update_coordinator"]
ha_ent  = sys.modules["homeassistant.helpers.entity"]
ha_ep   = sys.modules["homeassistant.helpers.entity_platform"]
ha_er   = sys.modules["homeassistant.helpers.entity_registry"]
ha_dr   = sys.modules["homeassistant.helpers.device_registry"]
ha_sel  = sys.modules["homeassistant.helpers.selector"]
ha_sens = sys.modules["homeassistant.components.sensor"]
ha_bsens = sys.modules["homeassistant.components.binary_sensor"]
ha_exc  = sys.modules["homeassistant.exceptions"]


# ── Minimal type stubs ─────────────────────────────────────────────────────

class _ConfigEntry:
    options: dict = {}


class _HomeAssistant:
    def __init__(self):
        self.bus = _EventBus()


class _EventBus:
    def __init__(self):
        self.fired = []

    def async_fire(self, event_type: str, event_data: dict) -> None:
        self.fired.append((event_type, event_data))


class _UpdateFailed(Exception):
    pass


class _DataUpdateCoordinator:
    """Minimal stand-in for HA's DataUpdateCoordinator."""

    def __init__(self, hass, logger, *, name, update_interval):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data = None

    async def async_refresh(self):
        self.data = await self._async_update_data()

    async def _async_update_data(self):
        raise NotImplementedError


class _SensorEntity:
    """Minimal stand-in for HA's SensorEntity."""
    _attr_native_value = None
    extra_state_attributes: dict = {}


ha_ce.ConfigEntry    = _ConfigEntry   # type: ignore[attr-defined]
ha_core.HomeAssistant = _HomeAssistant  # type: ignore[attr-defined]
ha_uc.DataUpdateCoordinator = _DataUpdateCoordinator  # type: ignore[attr-defined]
ha_uc.UpdateFailed   = _UpdateFailed  # type: ignore[attr-defined]
ha_ent.Entity        = object         # type: ignore[attr-defined]
ha_ep.AddEntitiesCallback = object    # type: ignore[attr-defined]
ha_er.async_get      = lambda hass: types.SimpleNamespace(entities={})  # type: ignore[attr-defined]
ha_sel.SelectSelector = object        # type: ignore[attr-defined]
ha_sel.SelectSelectorConfig = dict    # type: ignore[attr-defined]
ha_sel.NumberSelector = object        # type: ignore[attr-defined]
ha_sel.NumberSelectorConfig = dict    # type: ignore[attr-defined]
ha_sel.NumberSelectorMode = types.SimpleNamespace(BOX="box", SLIDER="slider")  # type: ignore[attr-defined]
ha_sens.SensorEntity = _SensorEntity  # type: ignore[attr-defined]
ha_sens.SensorStateClass = types.SimpleNamespace(MEASUREMENT="measurement")  # type: ignore[attr-defined]

class _BinarySensorEntity:
    """Minimal stand-in for HA's BinarySensorEntity."""
    _attr_is_on = False

ha_bsens.BinarySensorEntity = _BinarySensorEntity  # type: ignore[attr-defined]
ha_bsens.BinarySensorDeviceClass = types.SimpleNamespace(  # type: ignore[attr-defined]
    PROBLEM="problem",
    PRESENCE="presence",
)
ha_exc.ConfigEntryAuthFailed = Exception  # type: ignore[attr-defined]

# DeviceInfo stub — just a named tuple-like container
class _DeviceInfo(dict):
    pass
ha_dr.DeviceInfo = _DeviceInfo  # type: ignore[attr-defined]

# config_entries needs a ConfigFlow base class too
class _ConfigFlow:
    pass
ha_ce.ConfigFlow = _ConfigFlow  # type: ignore[attr-defined]
