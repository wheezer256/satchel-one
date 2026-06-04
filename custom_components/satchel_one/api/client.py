"""Async HTTP client for the Satchel One API.

This is the ONLY file that makes HTTP requests. All other modules consume
typed models from models.py.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, List

from .const_api import (
    API_HOST,
    DEFAULT_HEADERS,
    ENDPOINT_AUTH,
    ENDPOINT_DETENTIONS,
    ENDPOINT_STUDENT_PRAISES,
    ENDPOINT_STUDENT_PRAISE_SUMMARY,
    ENDPOINT_STUDENTS,
    ENDPOINT_TODOS,
)
from .models import BehaviourEvent, BehaviourSummary, Child, Detention, Homework

if TYPE_CHECKING:
    import aiohttp


class RateLimitError(Exception):
    """Raised when the API returns HTTP 429."""


class ServerError(Exception):
    """Raised when the API returns a 5xx status."""


class AuthError(Exception):
    """Raised on invalid credentials or expired/invalid token."""


class SatchelOneClient:
    def __init__(self, session: "aiohttp.ClientSession", token: str) -> None:
        self._session = session
        self._token = token

    def _headers(self) -> dict:
        return {**DEFAULT_HEADERS, "Authorization": f"Bearer {self._token}"}

    def _cb(self) -> int:
        return int(time.time() * 1000)

    async def _get(self, path: str, params: dict) -> dict:
        url = f"{API_HOST}{path}"
        params["_cb"] = self._cb()
        async with self._session.get(url, headers=self._headers(), params=params) as resp:
            if resp.status == 429:
                raise RateLimitError("Rate limited by Satchel One API")
            if resp.status >= 500:
                raise ServerError(f"Satchel One API returned {resp.status}")
            return await resp.json()

    async def get_children(self) -> List[Child]:
        data = await self._get(ENDPOINT_STUDENTS, {})
        return [Child.from_dict(s) for s in data["students"]]

    async def get_homework(self, student_id: int) -> List[Homework]:
        data = await self._get(ENDPOINT_TODOS, {"student_id": student_id})
        return [Homework.from_dict(t) for t in data["todos"]]

    async def get_behaviour_praises(self, student_id: int) -> List[BehaviourEvent]:
        data = await self._get(ENDPOINT_STUDENT_PRAISES, {"student_id": student_id})
        return [BehaviourEvent.from_dict(p) for p in data["data"]["student_praises"]]

    async def get_behaviour_summary(self, student_id: int) -> BehaviourSummary:
        path = ENDPOINT_STUDENT_PRAISE_SUMMARY.format(student_id=student_id)
        data = await self._get(path, {})
        return BehaviourSummary.from_dict(data["student_praise_summary"])

    async def get_detentions(self, student_id: int) -> List[Detention]:
        data = await self._get(ENDPOINT_DETENTIONS, {"student_id": student_id})
        return [Detention.from_dict(d) for d in data["data"]["detentions"]]

    async def login(self, username: str, password: str) -> str:
        """Authenticate with the Satchel One API. Returns the bearer token."""
        url = f"{API_HOST}{ENDPOINT_AUTH}"
        data = {
            "grant_type": "password",
            "username": username,
            "password": password,
        }
        async with self._session.post(url, headers=DEFAULT_HEADERS, data=data) as resp:
            if resp.status == 401:
                raise AuthError("Invalid credentials")
            if resp.status >= 500:
                raise ServerError(f"Satchel One API returned {resp.status}")
            payload = await resp.json()
        self._token = payload["access_token"]
        return self._token
