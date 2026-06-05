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
    token = await client.login("parent@example.com", "password123", 900001)
    assert token == "test-access-token-abc123"


@pytest.mark.asyncio
async def test_login_updates_internal_token():
    payload = load("auth_token.json")
    session = _make_post_session(_make_response(payload))
    client = SatchelOneClient(session=session, token="old")
    await client.login("parent@example.com", "password123", 900001)
    assert client._token == "test-access-token-abc123"


@pytest.mark.asyncio
async def test_login_sends_credentials_in_post_body():
    payload = load("auth_token.json")
    session = _make_post_session(_make_response(payload))
    client = SatchelOneClient(session=session, token="")
    await client.login("parent@example.com", "s3cr3t", 900001)
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
        await client.login("bad@example.com", "wrong", 900001)


# ---------------------------------------------------------------------------
# Login request shape (replicates the maintained smhw-api flow)
#
# Login MUST POST to the root /oauth/token (not /api/oauth/token), with the
# web client_id/client_secret as query params and a body carrying school_id
# (Satchel scopes the credential check by school). Regression guards for the
# first-deploy login failure.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_posts_to_root_oauth_endpoint():
    from custom_components.satchel_one.api.const_api import OAUTH_TOKEN_URL
    payload = load("auth_token.json")
    session = _make_post_session(_make_response(payload))
    client = SatchelOneClient(session=session, token="")
    await client.login("parent@example.com", "password123", 900001)
    url = session.post.call_args[0][0]
    assert url == OAUTH_TOKEN_URL
    assert "/api/oauth/token" not in url  # the wrong, CDN-fronted route


@pytest.mark.asyncio
async def test_login_sends_client_credentials_as_query_params():
    from custom_components.satchel_one.api.const_api import CLIENT_ID, CLIENT_SECRET
    payload = load("auth_token.json")
    session = _make_post_session(_make_response(payload))
    client = SatchelOneClient(session=session, token="")
    await client.login("parent@example.com", "password123", 900001)
    params = session.post.call_args[1].get("params", {})
    assert params.get("client_id") == CLIENT_ID
    assert params.get("client_secret") == CLIENT_SECRET


@pytest.mark.asyncio
async def test_login_body_carries_school_id_and_verification_token():
    payload = load("auth_token.json")
    session = _make_post_session(_make_response(payload))
    client = SatchelOneClient(session=session, token="")
    await client.login("parent@example.com", "password123", 900001)
    data = session.post.call_args[1].get("data", {})
    assert data["school_id"] == 900001
    assert data["verification_token"] == ""


@pytest.mark.asyncio
async def test_get_sends_versioned_accept_header():
    from custom_components.satchel_one.api.const_api import API_ACCEPT
    payload = load("homework_upcoming.json")
    session = _make_session(_make_response(payload))
    client = SatchelOneClient(session=session, token="tok")
    await client.get_homework(STUDENT_ID)
    headers = session.get.call_args[1].get("headers", {})
    assert headers.get("Accept") == API_ACCEPT
    assert headers.get("Accept").startswith("application/smhw.v")


@pytest.mark.asyncio
async def test_get_raises_clean_error_on_4xx_html_body():
    """A 400 with an HTML body must raise ServerError (not a ContentTypeError
    from blindly calling .json())."""
    from custom_components.satchel_one.api.client import ServerError
    resp = _make_response({}, status=400)
    resp.text = AsyncMock(return_value="<html>Bad Request</html>")
    resp.json = AsyncMock(side_effect=AssertionError(".json() must not be called on a 4xx"))
    client = SatchelOneClient(session=_make_session(resp), token="tok")
    with pytest.raises(ServerError) as exc:
        await client.get_homework(STUDENT_ID)
    assert "400" in str(exc.value)


@pytest.mark.asyncio
async def test_get_raises_auth_error_on_403():
    resp = _make_response({}, status=403)
    resp.text = AsyncMock(return_value="forbidden")
    client = SatchelOneClient(session=_make_session(resp), token="tok")
    with pytest.raises(AuthError):
        await client.get_homework(STUDENT_ID)


# ---------------------------------------------------------------------------
# search_schools
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_schools_returns_school_list():
    from custom_components.satchel_one.api.models import School
    payload = load("school_search.json")
    session = _make_session(_make_response(payload))
    client = SatchelOneClient(session=session, token="")
    result = await client.search_schools("Greenfield")
    assert len(result) == 2
    assert all(isinstance(s, School) for s in result)
    assert result[0].id == 900001
    assert result[0].name == "Greenfield Academy"
    assert result[0].town == "Greenfield"


@pytest.mark.asyncio
async def test_search_schools_sends_no_auth_header():
    payload = load("school_search.json")
    session = _make_session(_make_response(payload))
    client = SatchelOneClient(session=session, token="")
    await client.search_schools("Greenfield")
    headers = session.get.call_args[1].get("headers", {})
    assert "Authorization" not in headers
    params = session.get.call_args[1].get("params", {})
    assert params.get("filter") == "Greenfield"


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
