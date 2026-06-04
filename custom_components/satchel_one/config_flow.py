"""Config flow for Satchel One.

Setup (config flow):
  Step 1 (async_step_user): parent email + password → login → fetch children list.
  Step 2 (async_step_link_children): for each child, pick a linked person.* entity.

Post-setup (options flow):
  async_step_init: edit poll intervals + re-map child→person links.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import aiohttp_client, entity_registry as er
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
)

from .api.client import AuthError, ServerError, SatchelOneClient
from .api.models import Child
from .const import DOMAIN, MIN_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required("email"): str,
        vol.Required("password"): str,
    }
)

_NONE_OPTION = "none"


def _person_options(hass: HomeAssistant) -> list[dict]:
    """Return all person.* entity IDs as selector options, plus a 'none' option."""
    registry = er.async_get(hass)
    options = [{"value": _NONE_OPTION, "label": "— none —"}]
    options += [
        {"value": entry.entity_id, "label": entry.entity_id}
        for entry in registry.entities.values()
        if entry.domain == "person"
    ]
    return options


_MIN_INTERVAL_MINUTES = MIN_UPDATE_INTERVAL // 60  # 5


class SatchelOneConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Satchel One."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "SatchelOneOptionsFlow":
        return SatchelOneOptionsFlow(config_entry)

    def __init__(self) -> None:
        self._token: str = ""
        self._email: str = ""
        self._children: list[Child] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            session = aiohttp_client.async_get_clientsession(self.hass)
            client = SatchelOneClient(session=session, token="")
            try:
                token = await client.login(user_input["email"], user_input["password"])
                children = await client.get_children()
            except AuthError:
                errors["base"] = "invalid_auth"
            except ServerError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Satchel One login")
                errors["base"] = "unknown"
            else:
                self._token = token
                self._email = user_input["email"]
                self._children = children
                return await self.async_step_link_children()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def async_step_link_children(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            child_person_map = {
                str(child.id): user_input.get(f"child_{child.id}", _NONE_OPTION)
                for child in self._children
            }
            # Replace "none" sentinel with None
            child_person_map = {
                k: (None if v == _NONE_OPTION else v)
                for k, v in child_person_map.items()
            }
            return self.async_create_entry(
                title=f"Satchel One ({self._email})",
                data={
                    "email": self._email,
                    "token": self._token,
                    "children": [
                        {"id": c.id, "name": c.name} for c in self._children
                    ],
                },
                options={"child_person_map": child_person_map},
            )

        person_options = _person_options(self.hass)
        schema_fields: dict = {}
        for child in self._children:
            schema_fields[vol.Optional(f"child_{child.id}")] = SelectSelector(
                SelectSelectorConfig(options=person_options)
            )

        return self.async_show_form(
            step_id="link_children",
            data_schema=vol.Schema(schema_fields),
            description_placeholders={
                "child_names": ", ".join(c.name for c in self._children)
            },
        )

    async def async_step_reauth(self, user_input: dict[str, Any] | None = None):
        """Handle re-authentication when the token expires or credentials change."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            session = aiohttp_client.async_get_clientsession(self.hass)
            client = SatchelOneClient(session=session, token="")
            try:
                token = await client.login(reauth_entry.data["email"], user_input["password"])
            except AuthError:
                errors["base"] = "invalid_auth"
            except ServerError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Satchel One reauth")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={"token": token},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required("password"): str}),
            description_placeholders={"email": reauth_entry.data.get("email", "")},
            errors=errors,
        )


class SatchelOneOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Satchel One — poll intervals and child→person mapping."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            # Enforce the 5-minute floor
            user_input["homework_interval_minutes"] = max(
                int(user_input["homework_interval_minutes"]), _MIN_INTERVAL_MINUTES
            )
            user_input["behaviour_interval_minutes"] = max(
                int(user_input["behaviour_interval_minutes"]), _MIN_INTERVAL_MINUTES
            )
            # Normalise person map: replace "none" sentinel with None
            child_person_map = {
                str(child["id"]): (
                    None
                    if user_input.get(f"child_{child['id']}", "none") == "none"
                    else user_input.pop(f"child_{child['id']}", None)
                )
                for child in self._entry.data.get("children", [])
            }
            # Remove per-child keys from top-level options dict
            for child in self._entry.data.get("children", []):
                user_input.pop(f"child_{child['id']}", None)
            user_input["child_person_map"] = child_person_map
            return self.async_create_entry(title="", data=user_input)

        current = self._entry.options
        person_opts = _person_options(self.hass)

        schema_fields: dict = {
            vol.Optional(
                "homework_interval_minutes",
                default=current.get("homework_interval_minutes", 30),
            ): NumberSelector(NumberSelectorConfig(min=_MIN_INTERVAL_MINUTES, max=120, mode=NumberSelectorMode.BOX)),
            vol.Optional(
                "behaviour_interval_minutes",
                default=current.get("behaviour_interval_minutes", 15),
            ): NumberSelector(NumberSelectorConfig(min=_MIN_INTERVAL_MINUTES, max=60, mode=NumberSelectorMode.BOX)),
        }

        existing_map = current.get("child_person_map", {})
        for child in self._entry.data.get("children", []):
            schema_fields[vol.Optional(f"child_{child['id']}")] = SelectSelector(
                SelectSelectorConfig(options=person_opts)
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_fields),
        )
