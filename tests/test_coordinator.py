"""Tests for coordinator.py — homework and behaviour fetch, delta detection, event firing."""

import json
import pathlib
import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.satchel_one.api.models import BehaviourEvent, BehaviourSummary, Detention, Homework
from custom_components.satchel_one.coordinator import BehaviourCoordinator, HomeworkCoordinator
from custom_components.satchel_one.const import (
    EVENT_BEHAVIOUR_CREDIT,
    EVENT_BEHAVIOUR_DEMERIT,
    EVENT_HOMEWORK_NEW,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
STUDENT_ID = 99999999


def load_homework():
    data = json.loads((FIXTURES / "homework_upcoming.json").read_text())
    return [Homework.from_dict(t) for t in data["todos"]]


def _make_hass():
    from tests.conftest import _HomeAssistant
    return _HomeAssistant()


def _make_client(homework=None):
    client = MagicMock()
    client.get_homework = AsyncMock(return_value=homework or load_homework())
    return client


# ---------------------------------------------------------------------------
# Basic data fetch
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_coordinator_fetch_returns_homework_list():
    hass = _make_hass()
    client = _make_client()
    coord = HomeworkCoordinator(hass=hass, client=client, student_id=STUDENT_ID)
    await coord.async_refresh()
    assert "homework" in coord.data
    assert len(coord.data["homework"]) == 2


@pytest.mark.asyncio
async def test_coordinator_calls_client_with_student_id():
    hass = _make_hass()
    client = _make_client()
    coord = HomeworkCoordinator(hass=hass, client=client, student_id=STUDENT_ID)
    await coord.async_refresh()
    client.get_homework.assert_called_once_with(STUDENT_ID)


# ---------------------------------------------------------------------------
# First-fetch seeding: must NOT fire events
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_first_fetch_fires_no_events():
    hass = _make_hass()
    client = _make_client()
    coord = HomeworkCoordinator(hass=hass, client=client, student_id=STUDENT_ID)
    await coord.async_refresh()
    new_hw_events = [e for e in hass.bus.fired if e[0] == EVENT_HOMEWORK_NEW]
    assert new_hw_events == []


# ---------------------------------------------------------------------------
# Delta detection: new item on second fetch fires event
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_new_homework_on_second_fetch_fires_event():
    hass = _make_hass()
    initial = load_homework()[:1]  # one item
    new_item = load_homework()[1]  # second item arrives later

    client = _make_client(homework=initial)
    coord = HomeworkCoordinator(hass=hass, client=client, student_id=STUDENT_ID)
    await coord.async_refresh()  # first fetch — seeds, no events

    client.get_homework = AsyncMock(return_value=initial + [new_item])
    await coord.async_refresh()  # second fetch — new item

    events = [e for e in hass.bus.fired if e[0] == EVENT_HOMEWORK_NEW]
    assert len(events) == 1
    assert events[0][1]["task_id"] == new_item.id
    assert events[0][1]["title"] == new_item.title


@pytest.mark.asyncio
async def test_already_seen_item_does_not_refire():
    hass = _make_hass()
    homework = load_homework()
    client = _make_client(homework=homework)
    coord = HomeworkCoordinator(hass=hass, client=client, student_id=STUDENT_ID)

    await coord.async_refresh()  # first fetch — seeds both items
    await coord.async_refresh()  # second fetch — same items, no new events

    events = [e for e in hass.bus.fired if e[0] == EVENT_HOMEWORK_NEW]
    assert events == []


# ---------------------------------------------------------------------------
# Event payload
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_new_homework_event_contains_required_fields():
    hass = _make_hass()
    initial = load_homework()[:1]
    new_item = load_homework()[1]

    client = _make_client(homework=initial)
    coord = HomeworkCoordinator(hass=hass, client=client, student_id=STUDENT_ID)
    await coord.async_refresh()

    client.get_homework = AsyncMock(return_value=initial + [new_item])
    await coord.async_refresh()

    _, payload = hass.bus.fired[0]
    for key in ("task_id", "title", "subject", "teacher", "due_date"):
        assert key in payload, f"missing key: {key}"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rate_limit_error_raises_update_failed():
    from homeassistant.helpers.update_coordinator import UpdateFailed
    from custom_components.satchel_one.api.client import RateLimitError

    hass = _make_hass()
    client = MagicMock()
    client.get_homework = AsyncMock(side_effect=RateLimitError("429"))
    coord = HomeworkCoordinator(hass=hass, client=client, student_id=STUDENT_ID)
    with pytest.raises(UpdateFailed):
        await coord.async_refresh()


@pytest.mark.asyncio
async def test_server_error_raises_update_failed():
    from homeassistant.helpers.update_coordinator import UpdateFailed
    from custom_components.satchel_one.api.client import ServerError

    hass = _make_hass()
    client = MagicMock()
    client.get_homework = AsyncMock(side_effect=ServerError("500"))
    coord = HomeworkCoordinator(hass=hass, client=client, student_id=STUDENT_ID)
    with pytest.raises(UpdateFailed):
        await coord.async_refresh()


# ===========================================================================
# BehaviourCoordinator
# ===========================================================================

def load_praises():
    data = json.loads((FIXTURES / "behaviour_praises.json").read_text())
    return [BehaviourEvent.from_dict(p) for p in data["student_praises"]]


def load_summary():
    data = json.loads((FIXTURES / "behaviour_summary.json").read_text())
    return BehaviourSummary.from_dict(data["student_praise_summary"])


def load_detentions(fixture="detentions.json"):
    data = json.loads((FIXTURES / fixture).read_text())
    return [Detention.from_dict(d) for d in data["detentions"]]


def _make_behaviour_client(praises=None, summary=None, detentions=None):
    client = MagicMock()
    client.get_behaviour_praises = AsyncMock(return_value=praises if praises is not None else load_praises())
    client.get_behaviour_summary = AsyncMock(return_value=summary or load_summary())
    client.get_detentions = AsyncMock(return_value=detentions if detentions is not None else load_detentions())
    return client


# ---------------------------------------------------------------------------
# Basic fetch
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_behaviour_coordinator_fetch_returns_praises_and_summary():
    hass = _make_hass()
    client = _make_behaviour_client()
    coord = BehaviourCoordinator(hass=hass, client=client, student_id=STUDENT_ID)
    await coord.async_refresh()
    assert "praises" in coord.data
    assert "summary" in coord.data
    assert len(coord.data["praises"]) == 4
    assert coord.data["summary"].total_positive_count == 100


@pytest.mark.asyncio
async def test_behaviour_coordinator_calls_client_with_student_id():
    hass = _make_hass()
    client = _make_behaviour_client()
    coord = BehaviourCoordinator(hass=hass, client=client, student_id=STUDENT_ID)
    await coord.async_refresh()
    client.get_behaviour_praises.assert_called_once_with(STUDENT_ID)
    client.get_behaviour_summary.assert_called_once_with(STUDENT_ID)


# ---------------------------------------------------------------------------
# First-fetch seeding: no events
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_behaviour_first_fetch_fires_no_events():
    hass = _make_hass()
    client = _make_behaviour_client()
    coord = BehaviourCoordinator(hass=hass, client=client, student_id=STUDENT_ID)
    await coord.async_refresh()
    assert hass.bus.fired == []


# ---------------------------------------------------------------------------
# Delta detection: credit event
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_new_positive_event_fires_credit():
    hass = _make_hass()
    initial = [p for p in load_praises() if p.positive][:1]
    new_positive = [p for p in load_praises() if p.positive][1]

    client = _make_behaviour_client(praises=initial)
    coord = BehaviourCoordinator(hass=hass, client=client, student_id=STUDENT_ID)
    await coord.async_refresh()

    client.get_behaviour_praises = AsyncMock(return_value=initial + [new_positive])
    await coord.async_refresh()

    events = [e for e in hass.bus.fired if e[0] == EVENT_BEHAVIOUR_CREDIT]
    assert len(events) == 1
    assert events[0][1]["points"] == new_positive.points


# ---------------------------------------------------------------------------
# Delta detection: demerit event
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_new_negative_event_fires_demerit():
    hass = _make_hass()
    initial = [p for p in load_praises() if not p.positive][:1]
    new_negative = [p for p in load_praises() if not p.positive][1]

    client = _make_behaviour_client(praises=initial)
    coord = BehaviourCoordinator(hass=hass, client=client, student_id=STUDENT_ID)
    await coord.async_refresh()

    client.get_behaviour_praises = AsyncMock(return_value=initial + [new_negative])
    await coord.async_refresh()

    events = [e for e in hass.bus.fired if e[0] == EVENT_BEHAVIOUR_DEMERIT]
    assert len(events) == 1
    assert events[0][1]["points"] == new_negative.points


# ---------------------------------------------------------------------------
# Event payload
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_credit_event_contains_required_fields():
    hass = _make_hass()
    initial = [p for p in load_praises() if p.positive][:1]
    new_positive = [p for p in load_praises() if p.positive][1]

    client = _make_behaviour_client(praises=initial)
    coord = BehaviourCoordinator(hass=hass, client=client, student_id=STUDENT_ID)
    await coord.async_refresh()

    client.get_behaviour_praises = AsyncMock(return_value=initial + [new_positive])
    await coord.async_refresh()

    _, payload = hass.bus.fired[0]
    for key in ("points", "severity", "reason", "teacher", "happened_on"):
        assert key in payload, f"missing key: {key}"


@pytest.mark.asyncio
async def test_credit_event_severity_is_abs_points():
    hass = _make_hass()
    # fixture has an event with points=5
    positive_events = [p for p in load_praises() if p.positive]
    initial = positive_events[:1]
    high_praise = positive_events[1]  # points=5

    client = _make_behaviour_client(praises=initial)
    coord = BehaviourCoordinator(hass=hass, client=client, student_id=STUDENT_ID)
    await coord.async_refresh()

    client.get_behaviour_praises = AsyncMock(return_value=initial + [high_praise])
    await coord.async_refresh()

    _, payload = hass.bus.fired[0]
    assert payload["severity"] == abs(high_praise.points)


# ---------------------------------------------------------------------------
# Already-seen items don't refire
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_already_seen_behaviour_event_does_not_refire():
    hass = _make_hass()
    praises = load_praises()
    client = _make_behaviour_client(praises=praises)
    coord = BehaviourCoordinator(hass=hass, client=client, student_id=STUDENT_ID)
    await coord.async_refresh()
    await coord.async_refresh()  # same data again
    assert hass.bus.fired == []


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_homework_event_includes_person_field():
    hass = _make_hass()
    initial = load_homework()[:1]
    new_item = load_homework()[1]
    client = _make_client(homework=initial)
    coord = HomeworkCoordinator(
        hass=hass, client=client, student_id=STUDENT_ID,
        child_name="Test Student", linked_person="person.test_student",
    )
    await coord.async_refresh()
    client.get_homework = AsyncMock(return_value=initial + [new_item])
    await coord.async_refresh()
    _, payload = hass.bus.fired[0]
    assert payload["person"] == "person.test_student"


@pytest.mark.asyncio
async def test_credit_event_includes_person_field():
    hass = _make_hass()
    initial = [p for p in load_praises() if p.positive][:1]
    new_positive = [p for p in load_praises() if p.positive][1]
    client = _make_behaviour_client(praises=initial)
    coord = BehaviourCoordinator(
        hass=hass, client=client, student_id=STUDENT_ID,
        child_name="Test Student", linked_person="person.test_student",
    )
    await coord.async_refresh()
    client.get_behaviour_praises = AsyncMock(return_value=initial + [new_positive])
    await coord.async_refresh()
    _, payload = hass.bus.fired[0]
    assert payload["person"] == "person.test_student"


@pytest.mark.asyncio
async def test_behaviour_rate_limit_raises_update_failed():
    from homeassistant.helpers.update_coordinator import UpdateFailed
    from custom_components.satchel_one.api.client import RateLimitError

    hass = _make_hass()
    client = MagicMock()
    client.get_behaviour_praises = AsyncMock(side_effect=RateLimitError("429"))
    client.get_behaviour_summary = AsyncMock(return_value=load_summary())
    client.get_detentions = AsyncMock(return_value=[])
    coord = BehaviourCoordinator(hass=hass, client=client, student_id=STUDENT_ID)
    with pytest.raises(UpdateFailed):
        await coord.async_refresh()


# ---------------------------------------------------------------------------
# Detentions in BehaviourCoordinator
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_behaviour_coordinator_fetches_detentions():
    hass = _make_hass()
    detentions = load_detentions("detentions_with_data.json")
    client = _make_behaviour_client(detentions=detentions)
    coord = BehaviourCoordinator(hass=hass, client=client, student_id=STUDENT_ID)
    await coord.async_refresh()
    assert "detentions" in coord.data
    assert len(coord.data["detentions"]) == 2


@pytest.mark.asyncio
async def test_behaviour_coordinator_calls_get_detentions_with_student_id():
    hass = _make_hass()
    client = _make_behaviour_client()
    coord = BehaviourCoordinator(hass=hass, client=client, student_id=STUDENT_ID)
    await coord.async_refresh()
    client.get_detentions.assert_called_once_with(STUDENT_ID)


@pytest.mark.asyncio
async def test_behaviour_coordinator_empty_detentions_ok():
    hass = _make_hass()
    client = _make_behaviour_client(detentions=[])
    coord = BehaviourCoordinator(hass=hass, client=client, student_id=STUDENT_ID)
    await coord.async_refresh()
    assert coord.data["detentions"] == []
