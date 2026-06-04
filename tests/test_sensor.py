"""Tests for sensor.py — all sensors."""

import json
import pathlib
import pytest
from unittest.mock import MagicMock

from custom_components.satchel_one.api.models import BehaviourEvent, BehaviourSummary, Homework
from custom_components.satchel_one.api.models import Detention
from custom_components.satchel_one.sensor import (
    ConductNetSensor,
    CreditsSensor,
    DemeritsSensor,
    DetentionsSensor,
    HomeworkDueSensor,
    NextHomeworkSensor,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
STUDENT_ID = 99999999
CHILD_NAME = "Test Student"


def load_homework():
    data = json.loads((FIXTURES / "homework_upcoming.json").read_text())
    return [Homework.from_dict(t) for t in data["todos"]]


def _make_coordinator(homework=None):
    coord = MagicMock()
    coord.data = {"homework": homework if homework is not None else load_homework()}
    return coord


# ---------------------------------------------------------------------------
# HomeworkDueSensor — native_value (count of outstanding tasks)
# ---------------------------------------------------------------------------

def test_homework_due_count_all_incomplete():
    coord = _make_coordinator()
    sensor = HomeworkDueSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.native_value == 2


def test_homework_due_count_excludes_completed():
    hw = load_homework()
    hw[0] = Homework(
        id=hw[0].id, title=hw[0].title, subject=hw[0].subject,
        teacher_name=hw[0].teacher_name, class_group=hw[0].class_group,
        due_on=hw[0].due_on, issued_at=hw[0].issued_at,
        completed=True, has_attachments=hw[0].has_attachments,
        submission_type=hw[0].submission_type,
    )
    coord = _make_coordinator(hw)
    sensor = HomeworkDueSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.native_value == 1


def test_homework_due_count_zero_when_all_done():
    hw = load_homework()
    completed = [
        Homework(
            id=h.id, title=h.title, subject=h.subject, teacher_name=h.teacher_name,
            class_group=h.class_group, due_on=h.due_on, issued_at=h.issued_at,
            completed=True, has_attachments=h.has_attachments, submission_type=h.submission_type,
        )
        for h in hw
    ]
    coord = _make_coordinator(completed)
    sensor = HomeworkDueSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.native_value == 0


def test_homework_due_returns_none_when_no_data():
    coord = MagicMock()
    coord.data = None
    sensor = HomeworkDueSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.native_value is None


# ---------------------------------------------------------------------------
# HomeworkDueSensor — extra_state_attributes
# ---------------------------------------------------------------------------

def test_homework_due_attributes_contain_task_list():
    coord = _make_coordinator()
    sensor = HomeworkDueSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    attrs = sensor.extra_state_attributes
    assert "tasks" in attrs
    assert len(attrs["tasks"]) == 2


def test_homework_due_attributes_task_has_required_keys():
    coord = _make_coordinator()
    sensor = HomeworkDueSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    task = sensor.extra_state_attributes["tasks"][0]
    for key in ("title", "subject", "due_on", "teacher_name"):
        assert key in task, f"missing key: {key}"


def test_homework_due_attributes_empty_when_no_data():
    coord = MagicMock()
    coord.data = None
    sensor = HomeworkDueSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.extra_state_attributes == {}


# ---------------------------------------------------------------------------
# NextHomeworkSensor — native_value (ISO timestamp of next due item)
# ---------------------------------------------------------------------------

def test_next_homework_returns_earliest_due_date():
    coord = _make_coordinator()
    sensor = NextHomeworkSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    # Both fixture items are due 2030-01-15; just check it returns one of them
    assert sensor.native_value is not None
    assert "2030-01-15" in sensor.native_value


def test_next_homework_skips_completed_tasks():
    hw = load_homework()
    # Mark first item completed, leave second
    completed_first = [
        Homework(
            id=hw[0].id, title=hw[0].title, subject=hw[0].subject, teacher_name=hw[0].teacher_name,
            class_group=hw[0].class_group, due_on="2026-06-01T00:00:00+00:00",
            issued_at=hw[0].issued_at, completed=True,
            has_attachments=hw[0].has_attachments, submission_type=hw[0].submission_type,
        ),
        hw[1],
    ]
    coord = _make_coordinator(completed_first)
    sensor = NextHomeworkSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.native_value == hw[1].due_on


def test_next_homework_returns_none_when_all_complete():
    hw = load_homework()
    all_done = [
        Homework(
            id=h.id, title=h.title, subject=h.subject, teacher_name=h.teacher_name,
            class_group=h.class_group, due_on=h.due_on, issued_at=h.issued_at,
            completed=True, has_attachments=h.has_attachments, submission_type=h.submission_type,
        )
        for h in hw
    ]
    coord = _make_coordinator(all_done)
    sensor = NextHomeworkSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.native_value is None


def test_next_homework_returns_none_when_no_data():
    coord = MagicMock()
    coord.data = None
    sensor = NextHomeworkSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.native_value is None


# ---------------------------------------------------------------------------
# Entity identity
# ---------------------------------------------------------------------------

def test_homework_due_unique_id():
    coord = _make_coordinator()
    sensor = HomeworkDueSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert str(STUDENT_ID) in sensor.unique_id


def test_next_homework_unique_id():
    coord = _make_coordinator()
    sensor = NextHomeworkSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert str(STUDENT_ID) in sensor.unique_id


# ===========================================================================
# Behaviour sensors
# ===========================================================================

def load_praises():
    data = json.loads((FIXTURES / "behaviour_praises.json").read_text())
    return [BehaviourEvent.from_dict(p) for p in data["data"]["student_praises"]]


def load_summary():
    data = json.loads((FIXTURES / "behaviour_summary.json").read_text())
    return BehaviourSummary.from_dict(data["student_praise_summary"])


def _make_behaviour_coordinator(praises=None, summary=None):
    coord = MagicMock()
    coord.data = {
        "praises": praises if praises is not None else load_praises(),
        "summary": summary or load_summary(),
    }
    return coord


# ---------------------------------------------------------------------------
# CreditsSensor
# ---------------------------------------------------------------------------

def test_credits_native_value_is_total_positive_count():
    coord = _make_behaviour_coordinator()
    sensor = CreditsSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.native_value == 100


def test_credits_returns_none_when_no_data():
    coord = MagicMock()
    coord.data = None
    sensor = CreditsSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.native_value is None


def test_credits_attributes_contain_recent_positive_events():
    coord = _make_behaviour_coordinator()
    sensor = CreditsSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    attrs = sensor.extra_state_attributes
    assert "recent_events" in attrs
    # Only positive events
    assert all(e["points"] > 0 for e in attrs["recent_events"])


def test_credits_unique_id():
    coord = _make_behaviour_coordinator()
    sensor = CreditsSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert str(STUDENT_ID) in sensor.unique_id


# ---------------------------------------------------------------------------
# DemeritsSensor
# ---------------------------------------------------------------------------

def test_demerits_native_value_is_total_negative_count():
    coord = _make_behaviour_coordinator()
    sensor = DemeritsSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.native_value == 40


def test_demerits_returns_none_when_no_data():
    coord = MagicMock()
    coord.data = None
    sensor = DemeritsSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.native_value is None


def test_demerits_returns_none_for_positive_only_school():
    """If no negative events exist and total_negative_count is 0, degrade to None (unknown)."""
    positive_only_summary = BehaviourSummary(
        student_id=STUDENT_ID,
        total_positive_count=50,
        total_negative_count=0,
        total_net_count=50,
        week_positive_count=2,
        week_negative_count=0,
        month_positive_count=5,
        month_negative_count=0,
    )
    positive_only_praises = [p for p in load_praises() if p.positive]
    coord = _make_behaviour_coordinator(praises=positive_only_praises, summary=positive_only_summary)
    sensor = DemeritsSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.native_value is None


def test_demerits_attributes_contain_recent_negative_events():
    coord = _make_behaviour_coordinator()
    sensor = DemeritsSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    attrs = sensor.extra_state_attributes
    assert "recent_events" in attrs
    assert all(e["points"] < 0 for e in attrs["recent_events"])


# ---------------------------------------------------------------------------
# ConductNetSensor
# ---------------------------------------------------------------------------

def test_conduct_net_value_is_total_net_count():
    coord = _make_behaviour_coordinator()
    sensor = ConductNetSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.native_value == 60  # total_net_count from fixture


def test_conduct_net_returns_none_when_no_data():
    coord = MagicMock()
    coord.data = None
    sensor = ConductNetSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.native_value is None


def test_conduct_net_attributes_contain_week_and_month_counts():
    coord = _make_behaviour_coordinator()
    sensor = ConductNetSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    attrs = sensor.extra_state_attributes
    for key in ("week_positive", "week_negative", "month_positive", "month_negative"):
        assert key in attrs, f"missing: {key}"


def test_conduct_net_unique_id():
    coord = _make_behaviour_coordinator()
    sensor = ConductNetSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert str(STUDENT_ID) in sensor.unique_id


# ===========================================================================
# linked_person attribute on all sensors
# ===========================================================================

def _make_entry(person_entity_id=None):
    entry = MagicMock()
    entry.options = {
        "child_person_map": {str(STUDENT_ID): person_entity_id or "none"}
    }
    return entry


def test_homework_due_linked_person_attribute_set():
    coord = _make_coordinator()
    entry = _make_entry("person.test_student")
    sensor = HomeworkDueSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME, entry=entry)
    assert sensor.extra_state_attributes.get("linked_person") == "person.test_student"


def test_homework_due_linked_person_none_when_not_mapped():
    coord = _make_coordinator()
    entry = _make_entry(None)
    sensor = HomeworkDueSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME, entry=entry)
    assert sensor.extra_state_attributes.get("linked_person") is None


def test_credits_linked_person_attribute_set():
    coord = _make_behaviour_coordinator()
    entry = _make_entry("person.test_student")
    sensor = CreditsSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME, entry=entry)
    assert sensor.extra_state_attributes.get("linked_person") == "person.test_student"


def test_demerits_linked_person_attribute_set():
    coord = _make_behaviour_coordinator()
    entry = _make_entry("person.test_student")
    sensor = DemeritsSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME, entry=entry)
    assert sensor.extra_state_attributes.get("linked_person") == "person.test_student"


def test_conduct_net_linked_person_attribute_set():
    coord = _make_behaviour_coordinator()
    entry = _make_entry("person.test_student")
    sensor = ConductNetSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME, entry=entry)
    assert sensor.extra_state_attributes.get("linked_person") == "person.test_student"


# ===========================================================================
# DeviceInfo on all sensors
# ===========================================================================

def test_homework_due_has_device_info():
    coord = _make_coordinator()
    sensor = HomeworkDueSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.device_info is not None


def test_credits_has_device_info():
    coord = _make_behaviour_coordinator()
    sensor = CreditsSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.device_info is not None


# ===========================================================================
# DetentionsSensor
# ===========================================================================

def _make_detention(id, scheduled_at, description="Detention", location=None):
    return Detention(id=id, description=description, scheduled_at=scheduled_at, location=location)


def _make_behaviour_coordinator_with_detentions(detentions):
    coord = MagicMock()
    coord.data = {
        "praises": load_praises(),
        "summary": load_summary(),
        "detentions": detentions,
    }
    return coord


def test_detentions_count_upcoming():
    detentions = [
        _make_detention(1, "2026-06-10T15:30:00+00:00"),
        _make_detention(2, "2026-06-12T12:00:00+00:00"),
    ]
    coord = _make_behaviour_coordinator_with_detentions(detentions)
    sensor = DetentionsSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.native_value == 2


def test_detentions_zero_when_empty():
    coord = _make_behaviour_coordinator_with_detentions([])
    sensor = DetentionsSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.native_value == 0


def test_detentions_returns_none_when_no_data():
    coord = MagicMock()
    coord.data = None
    sensor = DetentionsSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.native_value is None


def test_detentions_attributes_contain_list():
    detentions = [
        _make_detention(1, "2026-06-10T15:30:00+00:00", "After-school", "Room 12"),
    ]
    coord = _make_behaviour_coordinator_with_detentions(detentions)
    sensor = DetentionsSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    attrs = sensor.extra_state_attributes
    assert "detentions" in attrs
    assert attrs["detentions"][0]["scheduled_at"] == "2026-06-10T15:30:00+00:00"
    assert attrs["detentions"][0]["description"] == "After-school"
    assert attrs["detentions"][0]["location"] == "Room 12"


def test_detentions_unique_id():
    coord = _make_behaviour_coordinator_with_detentions([])
    sensor = DetentionsSensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert str(STUDENT_ID) in sensor.unique_id
