from __future__ import annotations

from collections import OrderedDict
from dataclasses import replace
from itertools import count
from typing import Iterable

from .models import AccountRecord, CourseRecord, EnrollmentRecord, StudentRecord, utc_now


class RepositoryError(Exception):
    pass


class NotFoundError(RepositoryError):
    pass


class ConflictError(RepositoryError):
    pass


class ValidationError(RepositoryError):
    pass


class CourseFullError(RepositoryError):
    pass


class InMemoryCollegeARepository:
    def __init__(self, college_id: str = "A") -> None:
        self.college_id = college_id
        self._enrollment_seq = count(1)
        self.accounts: dict[str, AccountRecord] = {}
        self.students: dict[str, StudentRecord] = {}
        self.courses: dict[str, CourseRecord] = {}
        self.enrollments: dict[str, EnrollmentRecord] = {}
        self.enrollment_key_index: dict[tuple[str, str], str] = {}
        self.enrollment_history: OrderedDict[str, EnrollmentRecord] = OrderedDict()
        self.outbound_requests: OrderedDict[str, dict] = OrderedDict()
        self._seed()

    def _seed(self) -> None:
        self.accounts = {
            "a_student1": AccountRecord("a_student1", "123456", "STUD", "S2024001"),
            "a_student2": AccountRecord("a_student2", "123456", "STUD", "S2024002"),
            "a_admin": AccountRecord("a_admin", "admin1", "ADMN", None),
        }
        self.students = {
            "S2024001": StudentRecord("S2024001", "张小明", "男", "计算机", "a_student1"),
            "S2024002": StudentRecord("S2024002", "李小红", "女", "软件工程", "a_student2"),
            "S2024003": StudentRecord("S2024003", "王小林", "男", "数据科学", "a_student1"),
        }
        self.courses = {
            "A001": CourseRecord("A001", "数据库系统", 0, 3, "张老师", "1-301", "Y", 2),
            "A002": CourseRecord("A002", "Java设计", 0, 4, "李老师", "2-201", "N", 30),
            "A003": CourseRecord("A003", "数仓基础", 0, 2, "王老师", "3-105", "Y", 30),
        }

    def get_account(self, username: str) -> AccountRecord | None:
        return self.accounts.get(username)

    def get_student(self, student_id: str) -> StudentRecord | None:
        return self.students.get(student_id)

    def get_student_by_account(self, username: str) -> StudentRecord | None:
        return next((s for s in self.students.values() if s.account_username == username), None)

    def get_course(self, course_id: str) -> CourseRecord | None:
        return self.courses.get(course_id)

    def get_enrollment(self, enrollment_id: str) -> EnrollmentRecord | None:
        return self.enrollments.get(enrollment_id) or self.enrollment_history.get(enrollment_id)

    def get_outbound_request(self, enrollment_id: str) -> dict | None:
        return self.outbound_requests.get(enrollment_id)

    def list_courses(self) -> list[CourseRecord]:
        return list(self.courses.values())

    def list_shared_courses(self) -> list[CourseRecord]:
        return [course for course in self.courses.values() if course.shared.upper() == "Y"]

    def _active_enrollment_count(self, course_id: str) -> int:
        return sum(1 for item in self.enrollments.values() if item.course_id == course_id and item.status == "ENROLLED")

    def _next_enrollment_id(self, prefix: str = "E") -> str:
        return f"{prefix}{utc_now().strftime('%Y%m%d')}{next(self._enrollment_seq):04d}"

    def _store_enrollment(self, record: EnrollmentRecord) -> EnrollmentRecord:
        self.enrollments[record.enrollment_id] = record
        self.enrollment_history[record.enrollment_id] = record
        self.enrollment_key_index[(record.student_id, record.course_id)] = record.enrollment_id
        return record

    def create_local_enrollment(self, student_id: str, course_id: str, score: int = 0) -> tuple[EnrollmentRecord, bool]:
        student = self.get_student(student_id)
        course = self.get_course(course_id)
        if student is None:
            raise NotFoundError("student not found")
        if course is None:
            raise NotFoundError("course not found")
        key = (student_id, course_id)
        existing_id = self.enrollment_key_index.get(key)
        if existing_id is not None:
            existing = self.enrollments.get(existing_id)
            if existing is not None and existing.status == "ENROLLED":
                return existing, False
        if self._active_enrollment_count(course_id) >= course.capacity:
            raise CourseFullError("course is full")
        record = EnrollmentRecord(
            enrollment_id=self._next_enrollment_id(),
            student_id=student_id,
            course_id=course_id,
            score=score,
            source_college_id=self.college_id,
            target_college_id=self.college_id,
            origin="LOCAL",
        )
        return self._store_enrollment(record), True

    def apply_inbound_writeback(
        self,
        *,
        source_college_id: str,
        target_college_id: str,
        student_id: str,
        course_id: str,
        score: int,
        status: str = "ENROLLED",
        enrollment_id: str | None = None,
    ) -> tuple[EnrollmentRecord, bool]:
        if target_college_id != self.college_id:
            raise ValidationError("target college mismatch")
        student = self.get_student(student_id)
        course = self.get_course(course_id)
        if student is None:
            raise NotFoundError("student not found")
        if course is None:
            raise NotFoundError("course not found")
        if course.shared.upper() != "Y" and source_college_id != self.college_id:
            raise ValidationError("course is not shared")
        key = (student_id, course_id)
        existing_id = self.enrollment_key_index.get(key)
        if existing_id is not None:
            existing = self.enrollments.get(existing_id)
            if existing is not None and existing.status == "ENROLLED":
                return existing, False
        if self._active_enrollment_count(course_id) >= course.capacity:
            raise CourseFullError("course is full")
        record = EnrollmentRecord(
            enrollment_id=enrollment_id or self._next_enrollment_id(),
            student_id=student_id,
            course_id=course_id,
            score=score,
            source_college_id=source_college_id,
            target_college_id=target_college_id,
            origin="INBOUND",
            status=status,
        )
        return self._store_enrollment(record), True

    def withdraw_enrollment(
        self,
        *,
        enrollment_id: str,
        student_id: str | None = None,
        course_id: str | None = None,
    ) -> tuple[EnrollmentRecord, bool]:
        record = self.enrollments.get(enrollment_id) or self.enrollment_history.get(enrollment_id)
        if record is None and student_id and course_id:
            key = (student_id, course_id)
            record_id = self.enrollment_key_index.get(key)
            if record_id is not None:
                record = self.enrollments.get(record_id) or self.enrollment_history.get(record_id)
        if record is None:
            raise NotFoundError("enrollment not found")
        if record.status == "WITHDRAWN":
            return record, False
        active_id = self.enrollment_key_index.get((record.student_id, record.course_id))
        if active_id == record.enrollment_id:
            self.enrollments.pop(record.enrollment_id, None)
            self.enrollment_key_index.pop((record.student_id, record.course_id), None)
        updated = replace(record, status="WITHDRAWN", updated_at=utc_now())
        self.enrollment_history[record.enrollment_id] = updated
        self.enrollments.pop(record.enrollment_id, None)
        return updated, True

    def register_outbound_request(self, *, home_college_id: str, target_college_id: str, student_id: str, course_id: str, score: int) -> str:
        enrollment_id = self._next_enrollment_id()
        self.outbound_requests[enrollment_id] = {
            "enrollmentId": enrollment_id,
            "homeCollegeId": home_college_id,
            "targetCollegeId": target_college_id,
            "studentId": student_id,
            "courseId": course_id,
            "score": score,
            "status": "PENDING_WRITEBACK",
            "requestTime": utc_now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        return enrollment_id

    def withdraw_outbound_request(self, enrollment_id: str) -> dict:
        request = self.outbound_requests.get(enrollment_id)
        if request is None:
            raise NotFoundError("enrollment not found")
        if request["status"] == "WITHDRAWN":
            return request
        request["status"] = "WITHDRAWN"
        request["updatedAt"] = utc_now().strftime("%Y-%m-%d %H:%M:%S")
        return request

    def courses_to_dicts(self, courses: Iterable[CourseRecord]) -> list[dict[str, object]]:
        return [
            {
                "id": course.course_id,
                "name": course.name,
                "time": course.time,
                "score": course.score,
                "teacher": course.teacher,
                "location": course.location,
                "share": course.shared,
            }
            for course in courses
        ]

    def students_to_dicts(self, students: Iterable[StudentRecord]) -> list[dict[str, object]]:
        return [
            {
                "id": student.student_id,
                "name": student.name,
                "major": student.major,
                "gender": student.gender,
            }
            for student in students
        ]

    def enrollment_to_dict(self, record: EnrollmentRecord) -> dict[str, object]:
        return {
            "enrollmentId": record.enrollment_id,
            "studentId": record.student_id,
            "courseId": record.course_id,
            "score": record.score,
            "sourceCollegeId": record.source_college_id,
            "targetCollegeId": record.target_college_id,
            "origin": record.origin,
            "status": record.status,
        }
