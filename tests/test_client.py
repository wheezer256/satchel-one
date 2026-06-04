"""Tests for api/client.py — no live HTTP, responses stubbed via aiohttp mock."""

import json
import pathlib
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.satchel_one.api.client import SatchelOneClient, AuthError
from custom_components.satchel_one.api.models import (
    Child,
    Homework,
    BehaviourEvent,
    BehaviourSummary,
    Detention,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
STUDENT_ID = 99999999


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _make_response(payload: dict, status: int = 200) -> MagicMock:
    """Return a mock aiohttp response that yields payload as JSON."""
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=payload)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


def _make_session(response: MagicMock) -> MagicMock:
    session = MagicMock()
    session.get = MagicMock(return_value=response)
    return session


# ---------------------------------------------------------------------------
# get_homework
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_homework_returns_homework_list():
    payload = load("homework_upcoming.json")
    client = SatchelOneClient(session=_make_session(_make_response(payload)), token="tok")
    result = await client.get_homework(STUDENT_ID)
    assert len(result) == 2
    assert all(isinstance(h, Homework) for h in result)


@pytest.mark.asyncio
async def test_get_homework_maps_fields():
    payload = load("homework_upcoming.json")
    client = SatchelOneClient(session=_make_session(_make_response(payload)), token="tok")
    result = await client.get_homework(STUDENT_ID)
    assert result[0].id == 701
    assert result[0].title == "Read chapter 3"


@pytest.mark.asyncio
async def test_get_homework_includes_cache_buster():
    payload = load("homework_upcoming.json")
    session = _make_session(_make_response(payload))
    client = SatchelOneClient(session=session, token="tok")
    await client.get_homework(STUDENT_ID)
    call_kwargs = session.get.call_args
    url = call_kwargs[0][0] if call_kwargs[0] else call_kwargs[1].get("url", "")
    params = call_kwargs[1].get("params", {}) if call_kwargs[1] else {}
    assert "_cb" in params


# ---------------------------------------------------------------------------
# get_behaviour_praises
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_behaviour_praises_returns_list():
    payload = load("behaviour_praises.json")
    client = SatchelOneClient(session=_make_session(_make_response(payload)), token="tok")
    result = await client.get_behaviour_praises(STUDENT_ID)
    assert len(result) == 4
    assert all(isinstance(e, BehaviourEvent) for e in result)


@pytest.mark.asyncio
async def test_get_behaviour_praises_maps_fields():
    payload = load("behaviour_praises.json")
    client = SatchelOneClient(session=_make_session(_make_response(payload)), token="tok")
    result = await client.get_behaviour_praises(STUDENT_ID)
    assert result[0].points == -1
    assert result[0].positive is False


# ---------------------------------------------------------------------------
# get_behaviour_summary
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_behaviour_summary_returns_summary():
    payload = load("behaviour_summary.json")
    client = SatchelOneClient(session=_make_session(_make_response(payload)), token="tok")
    result = await client.get_behaviour_summary(STUDENT_ID)
    assert isinstance(result, BehaviourSummary)
    assert result.total_positive_count == 100


# ---------------------------------------------------------------------------
# get_detentions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_detentions_returns_empty_list():
    payload = load("detentions.json")
    client = SatchelOneClient(session=_make_session(_make_response(payload)), token="tok")
    result = await client.get_detentions(STUDENT_ID)
    assert result == []
    assert all(isinstance(d, Detention) for d in result)


# ---------------------------------------------------------------------------
# Auth header
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bearer_token_sent_in_auth_header():
    payload = load("homework_upcoming.json")
    session = _make_session(_make_response(payload))
    client = SatchelOneClient(session=session, token="secret-token")
    await client.get_homework(STUDENT_ID)
    call_kwargs = session.get.call_args[1]
    headers = call_kwargs.get("headers", {})
    assert headers.get("Authorization") == "Bearer secret-token"


# ---------------------------------------------------------------------------
# Rate-limit backoff (429)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_raises_on_429():
    from custom_components.satchel_one.api.client import RateLimitError
    resp_429 = _make_response({}, status=429)
    client = SatchelOneClient(session=_make_session(resp_429), token="tok")
    with pytest.raises(RateLimitError):
        await client.get_homework(STUDENT_ID)


# ---------------------------------------------------------------------------
# Server error (5xx)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_raises_on_5xx():
    from custom_components.satchel_one.api.client import ServerError
    resp_500 = _make_response({}, status=500)
    client = SatchelOneClient(session=_make_session(resp_500), token="tok")
    with pytest.raises(ServerError):
        await client.get_homework(STUDENT_ID)


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------

def _make_post_session(response: MagicMock) -> MagicMock:
    session = MagicMock()
    session.post = MagicMock(return_value=response)
    return session


@pytest.mark.asyncio
async def test_login_returns_token():
    payload = load("auth_token.json")
    session = _make_post_session(_make_response(payload))
    client = SatchelOneClient(session=session, token="")
    token = await client.login("parent@example.com", "password123")
    assert token == "test-access-token-abc123"


@pytest.mark.asyncio
async def test_login_updates_internal_token():
    payload = load("auth_token.json")
    session = _make_post_session(_make_response(payload))
    client = SatchelOneClient(session=session, token="old")
    await client.login("parent@example.com", "password123")
    assert client._token == "test-access-token-abc123"


@pytest.mark.asyncio
async def test_login_sends_credentials_in_post_body():
    payload = load("auth_token.json")
    session = _make_post_session(_make_response(payload))
    client = SatchelOneClient(session=session, token="")
    await client.login("parent@example.com", "s3cr3t")
    call_kwargs = session.post.call_args[1]
    data = call_kwargs.get("data", {})
    assert data["username"] == "parent@example.com"
    assert data["password"] == "s3cr3t"
    assert data["grant_type"] == "password"


@pytest.mark.asyncio
async def test_login_raises_on_401():
    resp = _make_response({}, status=401)
    client = SatchelOneClient(session=_make_post_session(resp), token="")
    with pytest.raises(AuthError):
        await client.login("bad@example.com", "wrong")


# ---------------------------------------------------------------------------
# Versioned Accept header
#
# The live API requires a versioned `application/smhw.v{N}+json` Accept header.
# Sending plain `application/json` makes the CDN return a 405 HTML/XML error
# page (never reaching the API), whose body explodes on resp.json() and
# surfaces as a generic "unknown" config-flow error. Regression guard.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_sends_versioned_accept_header():
    payload = load("auth_token.json")
    session = _make_post_session(_make_response(payload))
    client = SatchelOneClient(session=session, token="")
    await client.login("parent@example.com", "password123")
    headers = session.post.call_args[1].get("headers", {})
    accept = headers.get("Accept", "")
    assert accept.startswith("application/smhw.v") and accept.endswith("+json"), accept


@pytest.mark.asyncio
async def test_get_sends_versioned_accept_header():
    payload = load("homework_upcoming.json")
    session = _make_session(_make_response(payload))
    client = SatchelOneClient(session=session, token="tok")
    await client.get_homework(STUDENT_ID)
    headers = session.get.call_args[1].get("headers", {})
    accept = headers.get("Accept", "")
    assert accept.startswith("application/smhw.v") and accept.endswith("+json"), accept


# ---------------------------------------------------------------------------
# get_children
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_children_returns_child_list():
    payload = load("children.json")
    client = SatchelOneClient(session=_make_session(_make_response(payload)), token="tok")
    result = await client.get_children()
    assert len(result) == 2
    assert all(isinstance(c, Child) for c in result)


@pytest.mark.asyncio
async def test_get_children_maps_fields():
    payload = load("children.json")
    client = SatchelOneClient(session=_make_session(_make_response(payload)), token="tok")
    result = await client.get_children()
    assert result[0].id == 100001
    assert result[0].name == "Alex Jordan Doe"
    assert result[1].id == 100002
    assert result[1].year == "Year 7"


@pytest.mark.asyncio
async def test_get_children_sends_auth_header():
    payload = load("children.json")
    session = _make_session(_make_response(payload))
    client = SatchelOneClient(session=session, token="my-token")
    await client.get_children()
    headers = session.get.call_args[1].get("headers", {})
    assert headers.get("Authorization") == "Bearer my-token"
