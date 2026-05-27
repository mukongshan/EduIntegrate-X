from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AccountRecord:
    username: str
    password: str
    role: str
    student_id: str | None = None


@dataclass
class StudentRecord:
    student_id: str
    name: str
    gender: str
    major: str
    account_username: str


@dataclass
class CourseRecord:
    course_id: str
    name: str
    time: int
    score: int
    teacher: str
    location: str
    shared: str
    capacity: int = 30


@dataclass
class EnrollmentRecord:
    enrollment_id: str
    student_id: str
    course_id: str
    score: int
    source_college_id: str
    target_college_id: str
    origin: str
    status: str = "ENROLLED"
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
