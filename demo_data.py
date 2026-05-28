from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class DemoAccount:
    username: str
    password: str
    role: str
    student_id: str | None = None


@dataclass(frozen=True)
class DemoStudent:
    student_id: str
    name: str
    gender: str
    major: str
    account_username: str


@dataclass(frozen=True)
class DemoCourse:
    course_id: str
    name: str
    time: int
    score: int
    teacher: str
    location: str
    shared: str
    capacity: int


@dataclass(frozen=True)
class DemoEnrollment:
    enrollment_id: str
    student_id: str
    course_id: str
    score: int
    source_college_id: str
    target_college_id: str
    origin: str
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class CollegeDemoData:
    college_id: str
    accounts: list[DemoAccount]
    students: list[DemoStudent]
    courses: list[DemoCourse]
    enrollments: list[DemoEnrollment]


COURSE_TEMPLATES = [
    ("数据库系统", 32, 3),
    ("操作系统", 40, 4),
    ("XML集成", 32, 3),
    ("软件工程", 32, 3),
    ("数据挖掘", 32, 3),
    ("分布式", 32, 3),
    ("机器学习", 32, 3),
    ("Web开发", 24, 2),
    ("网络技术", 32, 3),
    ("人工智能", 32, 3),
]

MAJORS = ["计科", "软工", "数据", "信管", "AI"]


def generate_college_demo_data(college_id: str) -> CollegeDemoData:
    college_id = college_id.upper()
    lower_id = college_id.lower()
    student_prefix = "S" if college_id == "A" else college_id
    now = datetime(2026, 5, 28, 0, 0, 0, tzinfo=timezone.utc)

    accounts: list[DemoAccount] = []
    students: list[DemoStudent] = []
    for i in range(1, 51):
        username = _student_account(lower_id, i)
        student_id = f"{student_prefix}2024{i:03d}"
        accounts.append(DemoAccount(username, "123456", "STUD", student_id))
        students.append(
            DemoStudent(
                student_id=student_id,
                name=f"{college_id}学生{i:02d}",
                gender="男" if i % 2 else "女",
                major=MAJORS[(i - 1) % len(MAJORS)],
                account_username=username,
            )
        )
    accounts.append(DemoAccount(f"{lower_id}_admin", "admin1", "ADMN", None))

    courses = [
        DemoCourse(
            course_id=f"{college_id}{i:03d}",
            name=name,
            time=time,
            score=score,
            teacher=f"{college_id}师{i:02d}",
            location=f"{college_id}-{100 + i}",
            shared="Y" if i in {1, 3, 5, 6, 7} else "N",
            capacity=999,
        )
        for i, (name, time, score) in enumerate(COURSE_TEMPLATES, start=1)
    ]

    enrollments: list[DemoEnrollment] = []
    seq = 1
    for student_index, student in enumerate(students):
        for offset in range(5):
            course = courses[(student_index + offset) % len(courses)]
            enrollments.append(
                DemoEnrollment(
                    enrollment_id=f"E{college_id}{seq:06d}",
                    student_id=student.student_id,
                    course_id=course.course_id,
                    score=0,
                    source_college_id=college_id,
                    target_college_id=college_id,
                    origin="LOCAL",
                    status="ENROLLED",
                    created_at=now,
                    updated_at=now,
                )
            )
            seq += 1

    return CollegeDemoData(college_id, accounts, students, courses, enrollments)


def _student_account(lower_id: str, index: int) -> str:
    if index <= 2:
        return f"{lower_id}_student{index}"
    return f"{lower_id}stu{index:03d}"
