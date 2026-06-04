"""Tests for api/models.py — all run against fixture data, no live API."""

import json
import pathlib
import pytest
from custom_components.satchel_one.api.models import (
    Child,
    Homework,
    BehaviourEvent,
    BehaviourSummary,
    Detention,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


# ---------------------------------------------------------------------------
# Homework
# ---------------------------------------------------------------------------

class TestHomework:
    def test_parses_from_todo_dict(self):
        todo = load("homework_upcoming.json")["todos"][0]
        hw = Homework.from_dict(todo)
        assert hw.id == 701
        assert hw.title == "Read chapter 3"
        assert hw.subject == "Mathematics"
        assert hw.teacher_name == "Mr A. Example"
        assert hw.class_group == "9X/Ma1"
        assert hw.completed is False
        assert hw.has_attachments is True

    def test_due_on_is_string(self):
        todo = load("homework_upcoming.json")["todos"][0]
        hw = Homework.from_dict(todo)
        assert hw.due_on == "2030-01-15T00:00:00+00:00"

    def test_issued_at_is_string(self):
        todo = load("homework_upcoming.json")["todos"][0]
        hw = Homework.from_dict(todo)
        assert hw.issued_at == "2030-01-05T00:00:00+00:00"

    def test_parses_all_todos(self):
        todos = load("homework_upcoming.json")["todos"]
        items = [Homework.from_dict(t) for t in todos]
        assert len(items) == 2
        assert items[1].id == 702

    def test_submission_type_nullable(self):
        todo = load("homework_upcoming.json")["todos"][0]
        todo["submission_type"] = None
        hw = Homework.from_dict(todo)
        assert hw.submission_type is None


# ---------------------------------------------------------------------------
# BehaviourEvent
# ---------------------------------------------------------------------------

class TestBehaviourEvent:
    def test_parses_negative_event(self):
        praise = load("behaviour_praises.json")["data"]["student_praises"][0]
        event = BehaviourEvent.from_dict(praise)
        assert event.id == 801
        assert event.points == -1
        assert event.positive is False
        assert event.description == "Late to lesson"
        assert event.happened_on == "2030-01-10"
        assert event.comments == "Example note for testing."

    def test_parses_positive_event(self):
        praise = load("behaviour_praises.json")["data"]["student_praises"][1]
        event = BehaviourEvent.from_dict(praise)
        assert event.id == 802
        assert event.points == 1
        assert event.positive is True
        assert event.comments is None

    def test_parses_high_positive_points(self):
        praise = load("behaviour_praises.json")["data"]["student_praises"][2]
        event = BehaviourEvent.from_dict(praise)
        assert event.points == 5

    def test_parses_all_events(self):
        praises = load("behaviour_praises.json")["data"]["student_praises"]
        events = [BehaviourEvent.from_dict(p) for p in praises]
        assert len(events) == 4

    def test_staff_name_composed(self):
        praise = load("behaviour_praises.json")["data"]["student_praises"][0]
        event = BehaviourEvent.from_dict(praise)
        assert event.staff_name == "Mrs. Staff Member"


# ---------------------------------------------------------------------------
# BehaviourSummary
# ---------------------------------------------------------------------------

class TestBehaviourSummary:
    def test_parses_summary(self):
        data = load("behaviour_summary.json")["student_praise_summary"]
        summary = BehaviourSummary.from_dict(data)
        assert summary.student_id == 99999999
        assert summary.total_positive_count == 100
        assert summary.total_negative_count == 40
        assert summary.total_net_count == 60

    def test_week_and_month_counts(self):
        data = load("behaviour_summary.json")["student_praise_summary"]
        summary = BehaviourSummary.from_dict(data)
        assert summary.week_positive_count == 0
        assert summary.week_negative_count == 1
        assert summary.month_positive_count == 0
        assert summary.month_negative_count == 1


# ---------------------------------------------------------------------------
# Detention
# ---------------------------------------------------------------------------

class TestDetention:
    def test_empty_list_returns_no_detentions(self):
        detentions = load("detentions.json")["data"]["detentions"]
        items = [Detention.from_dict(d) for d in detentions]
        assert items == []

    def test_parses_detention_with_data(self):
        detention_dict = {
            "id": 5001,
            "description": "After-school detention",
            "scheduled_at": "2026-06-10T15:30:00+00:00",
            "location": "Room 12",
            "duration": 30,
        }
        d = Detention.from_dict(detention_dict)
        assert d.id == 5001
        assert d.description == "After-school detention"
        assert d.scheduled_at == "2026-06-10T15:30:00+00:00"
        assert d.location == "Room 12"

    def test_detention_location_optional(self):
        detention_dict = {"id": 5001, "description": "Detention", "scheduled_at": "2026-06-10T15:30:00+00:00"}
        d = Detention.from_dict(detention_dict)
        assert d.location is None


# ---------------------------------------------------------------------------
# Child
# ---------------------------------------------------------------------------

class TestChild:
    def test_parses_first_child(self):
        student = load("children.json")["students"][0]
        child = Child.from_dict(student)
        assert child.id == 100001
        assert child.forename == "Alex Jordan"
        assert child.surname == "Doe"
        assert child.year == "Year 10"
        assert child.school_id == 900001

    def test_name_property_combines_forename_and_surname(self):
        student = load("children.json")["students"][0]
        child = Child.from_dict(student)
        assert child.name == "Alex Jordan Doe"

    def test_parses_second_child(self):
        student = load("children.json")["students"][1]
        child = Child.from_dict(student)
        assert child.id == 100002
        assert child.name == "Sam Taylor Doe"
        assert child.year == "Year 7"

    def test_parses_all_children(self):
        students = load("children.json")["students"]
        children = [Child.from_dict(s) for s in students]
        assert len(children) == 2
