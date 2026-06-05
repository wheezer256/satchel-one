"""Typed dataclasses for Satchel One API responses."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class School:
    id: int
    name: str
    town: str

    @classmethod
    def from_dict(cls, data: dict) -> "School":
        return cls(
            id=data["id"],
            name=data["name"],
            town=data.get("town") or "",
        )


@dataclass
class Child:
    id: int
    forename: str
    surname: str
    year: str
    school_id: int

    @property
    def name(self) -> str:
        return f"{self.forename} {self.surname}"

    @classmethod
    def from_dict(cls, data: dict) -> "Child":
        return cls(
            id=data["id"],
            forename=data["forename"],
            surname=data["surname"],
            year=data["year"],
            school_id=data["school_id"],
        )


@dataclass
class Homework:
    id: int
    title: str
    subject: str
    teacher_name: str
    class_group: str
    due_on: str
    issued_at: str
    completed: bool
    has_attachments: bool
    submission_type: Optional[str]

    @classmethod
    def from_dict(cls, data: dict) -> "Homework":
        return cls(
            id=data["id"],
            title=data["class_task_title"],
            subject=data["subject"],
            teacher_name=data["teacher_name"],
            class_group=data["class_group_name"],
            due_on=data["due_on"],
            issued_at=data["issued_at"],
            completed=data["completed"],
            has_attachments=data["has_attachments"],
            submission_type=data.get("submission_type"),
        )


@dataclass
class BehaviourEvent:
    id: int
    points: int
    positive: bool
    description: str
    happened_on: str
    comments: Optional[str]
    staff_name: str

    @classmethod
    def from_dict(cls, data: dict) -> "BehaviourEvent":
        staff_name = " ".join(filter(None, [
            data.get("staff_member_title"),
            data.get("staff_member_forename"),
            data.get("staff_member_surname"),
        ]))
        return cls(
            id=data["id"],
            points=data["points"],
            positive=data["positive"],
            description=data["description"],
            happened_on=data["happened_on"],
            comments=data.get("comments"),
            staff_name=staff_name,
        )


@dataclass
class BehaviourSummary:
    student_id: int
    total_positive_count: int
    total_negative_count: int
    total_net_count: int
    week_positive_count: int
    week_negative_count: int
    month_positive_count: int
    month_negative_count: int

    @classmethod
    def from_dict(cls, data: dict) -> "BehaviourSummary":
        return cls(
            student_id=data["student_id"],
            total_positive_count=data["total_positive_count"],
            total_negative_count=data["total_negative_count"],
            total_net_count=data["total_count"],
            week_positive_count=data["week_positive_count"],
            week_negative_count=data["week_negative_count"],
            month_positive_count=data["month_positive_count"],
            month_negative_count=data["month_negative_count"],
        )


@dataclass
class Detention:
    id: int
    description: str
    scheduled_at: Optional[str]
    location: Optional[str]

    @classmethod
    def from_dict(cls, data: dict) -> "Detention":
        return cls(
            id=data["id"],
            description=data.get("description", ""),
            scheduled_at=data.get("scheduled_at"),
            location=data.get("location"),
        )
