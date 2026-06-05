"""DataUpdateCoordinators for Satchel One homework and behaviour data."""

from __future__ import annotations

import logging
import datetime
from typing import TYPE_CHECKING, Optional

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.client import RateLimitError, ServerError
from .const import (
    DEFAULT_BEHAVIOUR_UPDATE_INTERVAL,
    DEFAULT_HOMEWORK_UPDATE_INTERVAL,
    DOMAIN,
    EVENT_BEHAVIOUR_CREDIT,
    EVENT_BEHAVIOUR_DEMERIT,
    EVENT_HOMEWORK_COMPLETED,
    EVENT_HOMEWORK_NEW,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from .api.client import SatchelOneClient

_LOGGER = logging.getLogger(__name__)


class HomeworkCoordinator(DataUpdateCoordinator):
    def __init__(
        self,
        hass: "HomeAssistant",
        client: "SatchelOneClient",
        student_id: int,
        child_name: str = "",
        linked_person: Optional[str] = None,
        update_interval: datetime.timedelta | None = None,
    ) -> None:
        if update_interval is None:
            update_interval = datetime.timedelta(seconds=DEFAULT_HOMEWORK_UPDATE_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_homework_{student_id}",
            update_interval=update_interval,
        )
        self._client = client
        self._student_id = student_id
        self._child_name = child_name
        self._linked_person = linked_person
        self._seen_ids: set[int] = set()
        self._completed_ids: set[int] = set()
        self._first_fetch = True

    async def _async_update_data(self) -> dict:
        try:
            homework = await self._client.get_homework(self._student_id)
        except (RateLimitError, ServerError) as err:
            raise UpdateFailed(str(err)) from err

        new_items = [h for h in homework if h.id not in self._seen_ids]
        completed_now = {h.id for h in homework if h.completed}
        newly_completed = [
            h for h in homework if h.completed and h.id not in self._completed_ids
        ]

        if not self._first_fetch:
            for hw in new_items:
                self.hass.bus.async_fire(
                    EVENT_HOMEWORK_NEW,
                    {
                        "task_id": hw.id,
                        "title": hw.title,
                        "subject": hw.subject,
                        "teacher": hw.teacher_name,
                        "due_date": hw.due_on,
                        "person": self._linked_person,
                    },
                )
            for hw in newly_completed:
                self.hass.bus.async_fire(
                    EVENT_HOMEWORK_COMPLETED,
                    {
                        "task_id": hw.id,
                        "title": hw.title,
                        "subject": hw.subject,
                        "person": self._linked_person,
                    },
                )

        self._seen_ids.update(h.id for h in homework)
        self._completed_ids = completed_now
        self._first_fetch = False

        return {"homework": homework}


class BehaviourCoordinator(DataUpdateCoordinator):
    def __init__(
        self,
        hass: "HomeAssistant",
        client: "SatchelOneClient",
        student_id: int,
        child_name: str = "",
        linked_person: Optional[str] = None,
        update_interval: datetime.timedelta | None = None,
    ) -> None:
        if update_interval is None:
            update_interval = datetime.timedelta(seconds=DEFAULT_BEHAVIOUR_UPDATE_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_behaviour_{student_id}",
            update_interval=update_interval,
        )
        self._client = client
        self._student_id = student_id
        self._child_name = child_name
        self._linked_person = linked_person
        self._seen_ids: set[int] = set()
        self._first_fetch = True

    async def _async_update_data(self) -> dict:
        try:
            praises = await self._client.get_behaviour_praises(self._student_id)
            summary = await self._client.get_behaviour_summary(self._student_id)
            detentions = await self._client.get_detentions(self._student_id)
        except (RateLimitError, ServerError) as err:
            raise UpdateFailed(str(err)) from err

        new_items = [p for p in praises if p.id not in self._seen_ids]

        if not self._first_fetch:
            for praise in new_items:
                event_type = EVENT_BEHAVIOUR_CREDIT if praise.positive else EVENT_BEHAVIOUR_DEMERIT
                self.hass.bus.async_fire(
                    event_type,
                    {
                        "points": praise.points,
                        "severity": abs(praise.points),
                        "reason": praise.description,
                        "teacher": praise.staff_name,
                        "happened_on": praise.happened_on,
                        "person": self._linked_person,
                    },
                )

        self._seen_ids.update(p.id for p in praises)
        self._first_fetch = False

        return {"praises": praises, "summary": summary, "detentions": detentions}
