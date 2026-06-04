"""Tests for binary_sensor.py."""

import json
import pathlib
import pytest
from unittest.mock import MagicMock, patch
from datetime import date

from custom_components.satchel_one.api.models import Detention, Homework
from custom_components.satchel_one.binary_sensor import (
    DetentionTodayBinarySensor,
    OverdueHomeworkBinarySensor,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
STUDENT_ID = 99999999
CHILD_NAME = "Test Student"
TODAY = "2026-06-04"  # matches currentDate in context


def _hw(id, due_on, completed=False):
    return Homework(
        id=id, title="T", subject="S", teacher_name="T", class_group="G",
        due_on=due_on, issued_at="2026-05-01T00:00:00+00:00",
        completed=completed, has_attachments=False, submission_type=None,
    )


def _detention(id, scheduled_at):
    return Detention(id=id, description="D", scheduled_at=scheduled_at, location=None)


def _hw_coord(homework):
    coord = MagicMock()
    coord.data = {"homework": homework}
    return coord


def _beh_coord(detentions):
    coord = MagicMock()
    coord.data = {"praises": [], "summary": MagicMock(), "detentions": detentions}
    return coord


# ---------------------------------------------------------------------------
# OverdueHomeworkBinarySensor
# ---------------------------------------------------------------------------

def test_overdue_homework_on_when_past_due_incomplete():
    hw = [_hw(1, "2026-06-03T00:00:00+00:00")]  # due yesterday, incomplete
    coord = _hw_coord(hw)
    sensor = OverdueHomeworkBinarySensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    with patch("custom_components.satchel_one.binary_sensor.date") as mock_date:
        mock_date.today.return_value = date(2026, 6, 4)
        mock_date.fromisoformat = date.fromisoformat
        assert sensor.is_on is True


def test_overdue_homework_off_when_not_yet_due():
    hw = [_hw(1, "2026-06-08T00:00:00+00:00")]  # due in future
    coord = _hw_coord(hw)
    sensor = OverdueHomeworkBinarySensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    with patch("custom_components.satchel_one.binary_sensor.date") as mock_date:
        mock_date.today.return_value = date(2026, 6, 4)
        mock_date.fromisoformat = date.fromisoformat
        assert sensor.is_on is False


def test_overdue_homework_off_when_completed_even_if_past_due():
    hw = [_hw(1, "2026-06-03T00:00:00+00:00", completed=True)]
    coord = _hw_coord(hw)
    sensor = OverdueHomeworkBinarySensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    with patch("custom_components.satchel_one.binary_sensor.date") as mock_date:
        mock_date.today.return_value = date(2026, 6, 4)
        mock_date.fromisoformat = date.fromisoformat
        assert sensor.is_on is False


def test_overdue_homework_off_when_no_data():
    coord = MagicMock()
    coord.data = None
    sensor = OverdueHomeworkBinarySensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.is_on is False


def test_overdue_homework_unique_id():
    coord = _hw_coord([])
    sensor = OverdueHomeworkBinarySensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert str(STUDENT_ID) in sensor.unique_id


# ---------------------------------------------------------------------------
# DetentionTodayBinarySensor
# ---------------------------------------------------------------------------

def test_detention_today_on_when_scheduled_today():
    detentions = [_detention(1, f"{TODAY}T15:30:00+00:00")]
    coord = _beh_coord(detentions)
    sensor = DetentionTodayBinarySensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    with patch("custom_components.satchel_one.binary_sensor.date") as mock_date:
        mock_date.today.return_value = date(2026, 6, 4)
        mock_date.fromisoformat = date.fromisoformat
        assert sensor.is_on is True


def test_detention_today_off_when_scheduled_tomorrow():
    detentions = [_detention(1, "2026-06-05T15:30:00+00:00")]
    coord = _beh_coord(detentions)
    sensor = DetentionTodayBinarySensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    with patch("custom_components.satchel_one.binary_sensor.date") as mock_date:
        mock_date.today.return_value = date(2026, 6, 4)
        mock_date.fromisoformat = date.fromisoformat
        assert sensor.is_on is False


def test_detention_today_off_when_no_detentions():
    coord = _beh_coord([])
    sensor = DetentionTodayBinarySensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.is_on is False


def test_detention_today_off_when_no_data():
    coord = MagicMock()
    coord.data = None
    sensor = DetentionTodayBinarySensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.is_on is False


def test_detention_today_handles_none_scheduled_at():
    detentions = [Detention(id=1, description="D", scheduled_at=None, location=None)]
    coord = _beh_coord(detentions)
    sensor = DetentionTodayBinarySensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert sensor.is_on is False


def test_detention_today_unique_id():
    coord = _beh_coord([])
    sensor = DetentionTodayBinarySensor(coordinator=coord, child_id=STUDENT_ID, child_name=CHILD_NAME)
    assert str(STUDENT_ID) in sensor.unique_id
