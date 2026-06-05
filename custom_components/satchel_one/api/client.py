"""Async HTTP client for the Satchel One API.

This is the ONLY file that makes HTTP requests. All other modules consume
typed models from models.py.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, List

from .const_api import (
    API_HOST,
    BASE_HEADERS,
    CLIENT_ID,
    CLIENT_SECRET,
    DEFAULT_HEADERS,
    ENDPOINT_DETENTIONS,
    ENDPOINT_SCHOOL_SEARCH,
    ENDPOINT_STUDENT_PRAISES,
    ENDPOINT_STUDENT_PRAISE_SUMMARY,
    ENDPOINT_STUDENTS,
    ENDPOINT_TODOS,
    OAUTH_TOKEN_URL,
)
from .models import BehaviourEvent, BehaviourSummary, Child, Detention, Homework, School

if TYPE_CHECKING:
    import aiohttp

_LOGGER = logging.getLogger(__name__)


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
            if resp.status in (401, 403):
                raise AuthError(f"Satchel One API returned {resp.status} for {path}")
            if resp.status >= 400:
                # Read the body as text — error responses are often HTML/XML
                # (a CDN/error page), so calling .json() blindly would raise an
                # opaque ContentTypeError instead of a useful message.
                body = (await resp.text())[:300]
                _LOGGER.warning("Satchel One GET %s -> %s: %s", path, resp.status, body)
                raise ServerError(f"Satchel One API returned {resp.status} for {path}: {body}")
            return await resp.json()

    async def get_children(self) -> List[Child]:
        data = await self._get(ENDPOINT_STUDENTS, {})
        return [Child.from_dict(s) for s in data["students"]]

    async def get_homework(self, student_id: int) -> List[Homework]:
        data = await self._get(ENDPOINT_TODOS, {"student_id": student_id})
        return [Homework.from_dict(t) for t in data["todos"]]

    async def get_behaviour_praises(self, student_id: int) -> List[BehaviourEvent]:
        data = await self._get(ENDPOINT_STUDENT_PRAISES, {"student_id": student_id})
        return [BehaviourEvent.from_dict(p) for p in data["student_praises"]]

    async def get_behaviour_summary(self, student_id: int) -> BehaviourSummary:
        path = ENDPOINT_STUDENT_PRAISE_SUMMARY.format(student_id=student_id)
        data = await self._get(path, {})
        return BehaviourSummary.from_dict(data["student_praise_summary"])

    async def get_detentions(self, student_id: int) -> List[Detention]:
        data = await self._get(ENDPOINT_DETENTIONS, {"student_id": student_id})
        return [Detention.from_dict(d) for d in data["detentions"]]

    async def search_schools(self, query: str) -> List[School]:
        """Search public schools by name. Unauthenticated; needed to resolve the
        school_id required by login()."""
        url = f"{API_HOST}{ENDPOINT_SCHOOL_SEARCH}"
        params = {"filter": query, "limit": 20}
        async with self._session.get(url, headers=BASE_HEADERS, params=params) as resp:
            if resp.status >= 500:
                raise ServerError(f"Satchel One API returned {resp.status}")
            data = await resp.json()
        return [School.from_dict(s) for s in data["schools"]]

    async def login(self, username: str, password: str, school_id: int) -> str:
        """Authenticate via OAuth2 password grant. Returns the bearer (access) token.

        Replicates the maintained smhw-api flow: client_id/client_secret as query
        params, and a form body carrying the school_id (Satchel scopes the
        credential check by school) plus an empty verification_token.
        """
        params = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}
        data = {
            "grant_type": "password",
            "username": username,
            "password": password,
            "school_id": school_id,
            "verification_token": "",
        }
        async with self._session.post(
            OAUTH_TOKEN_URL, headers=BASE_HEADERS, params=params, data=data
        ) as resp:
            if resp.status == 401:
                raise AuthError("Invalid credentials")
            if resp.status >= 500:
                raise ServerError(f"Satchel One API returned {resp.status}")
            payload = await resp.json()
        # The web client uses access_token (not smhw_token) as the bearer.
        self._token = payload["access_token"]
        return self._token
