from __future__ import annotations

from datetime import datetime, timezone
from itertools import count
from typing import Any

import oracledb

from demo_data import generate_college_demo_data

from .models import AccountRecord, CourseRecord, EnrollmentRecord, StudentRecord
from .repository import CourseFullError, NotFoundError, ValidationError


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OracleCollegeBRepository:
    def __init__(
        self,
        *,
        dsn: str,
        user: str,
        password: str,
        college_id: str = "B",
        init_schema: bool = True,
        reset_data: bool = False,
    ) -> None:
        self.dsn = dsn
        self.user = user
        self.password = password
        self.college_id = college_id
        self._enrollment_seq = count(1)
        if init_schema:
            self._ensure_schema()
        if reset_data:
            self.reset_demo_data()
        else:
            self.seed_demo_data()

    def _connect(self) -> oracledb.Connection:
        return oracledb.connect(user=self.user, password=self.password, dsn=self.dsn)

    def _table_exists(self, cursor: Any, table_name: str) -> bool:
        cursor.execute("SELECT COUNT(1) FROM user_tables WHERE table_name = :name", name=table_name.upper())
        return int(cursor.fetchone()[0]) > 0

    def _ensure_schema(self) -> None:
        conn = self._connect()
        try:
            cursor = conn.cursor()
            if not self._table_exists(cursor, "ACCOUNT"):
                cursor.execute(
                    """
                    CREATE TABLE Account (
                        "账户名" varchar2(12) PRIMARY KEY,
                        "密码" varchar2(12) NOT NULL,
                        "级别" number(2) NOT NULL,
                        "客体" varchar2(9)
                    )
                    """
                )
            if not self._table_exists(cursor, "STUDENT"):
                cursor.execute(
                    """
                    CREATE TABLE Student (
                        "学号" varchar2(9) PRIMARY KEY,
                        "姓名" varchar2(10) NOT NULL,
                        "性别" varchar2(2) NOT NULL,
                        "专业" varchar2(16) NOT NULL,
                        "密码" varchar2(6) NOT NULL
                    )
                    """
                )
            if not self._table_exists(cursor, "COURSE"):
                cursor.execute(
                    """
                    CREATE TABLE Course (
                        "编号" varchar2(5) PRIMARY KEY,
                        "名称" varchar2(16) NOT NULL,
                        "课时" varchar2(2) NOT NULL,
                        "学分" varchar2(1) NOT NULL,
                        "老师" varchar2(10) NOT NULL,
                        "地点" varchar2(20) NOT NULL,
                        "共享" char(1) NOT NULL
                    )
                    """
                )
            if not self._table_exists(cursor, "ENROLLMENT"):
                cursor.execute(
                    """
                    CREATE TABLE Enrollment (
                        "课程编号" varchar2(5) NOT NULL,
                        "学号" varchar2(9) NOT NULL,
                        "得分" varchar2(3) NOT NULL,
                        CONSTRAINT pk_b_enrollment PRIMARY KEY ("课程编号", "学号")
                    )
                    """
                )
            if not self._table_exists(cursor, "ENROLLMENTLOG"):
                cursor.execute(
                    """
                    CREATE TABLE EnrollmentLog (
                        enrollment_id varchar2(24) PRIMARY KEY,
                        student_id varchar2(9) NOT NULL,
                        course_id varchar2(5) NOT NULL,
                        source_college_id varchar2(8) NOT NULL,
                        target_college_id varchar2(8) NOT NULL,
                        score number(3) NOT NULL,
                        origin varchar2(16) NOT NULL,
                        status varchar2(16) NOT NULL,
                        created_at timestamp NOT NULL,
                        updated_at timestamp NOT NULL
                    )
                    """
                )
            if not self._table_exists(cursor, "OUTBOUNDREQUESTLOG"):
                cursor.execute(
                    """
                    CREATE TABLE OutboundRequestLog (
                        enrollment_id varchar2(24) PRIMARY KEY,
                        home_college_id varchar2(8) NOT NULL,
                        target_college_id varchar2(8) NOT NULL,
                        student_id varchar2(9) NOT NULL,
                        course_id varchar2(5) NOT NULL,
                        score number(3) NOT NULL,
                        status varchar2(20) NOT NULL,
                        request_time varchar2(19) NOT NULL,
                        updated_at varchar2(19)
                    )
                    """
                )
            conn.commit()
        finally:
            conn.close()

    def reset_demo_data(self) -> None:
        conn = self._connect()
        try:
            cursor = conn.cursor()
            for table in ("OutboundRequestLog", "EnrollmentLog", "Enrollment", "Course", "Account", "Student"):
                if self._table_exists(cursor, table):
                    cursor.execute(f"DELETE FROM {table}")
            conn.commit()
        finally:
            conn.close()
        self.seed_demo_data()

    def seed_demo_data(self) -> None:
        data = generate_college_demo_data(self.college_id)
        now = data.enrollments[0].created_at.replace(tzinfo=None) if data.enrollments else _utc_now().replace(tzinfo=None)
        conn = self._connect()
        try:
            cursor = conn.cursor()
            if self._scalar(conn, "SELECT COUNT(1) FROM Account") == 0:
                cursor.executemany(
                    'INSERT INTO Account ("账户名", "密码", "级别", "客体") VALUES (:1, :2, :3, :4)',
                    [
                        (
                            account.username,
                            account.password,
                            9 if account.role == "ADMN" else 1,
                            account.student_id,
                        )
                        for account in data.accounts
                    ],
                )
            if self._scalar(conn, "SELECT COUNT(1) FROM Student") == 0:
                cursor.executemany(
                    'INSERT INTO Student ("学号", "姓名", "性别", "专业", "密码") VALUES (:1, :2, :3, :4, :5)',
                    [
                        (student.student_id, student.name, student.gender, student.major, "123456")
                        for student in data.students
                    ],
                )
            if self._scalar(conn, "SELECT COUNT(1) FROM Course") == 0:
                cursor.executemany(
                    'INSERT INTO Course ("编号", "名称", "课时", "学分", "老师", "地点", "共享") VALUES (:1, :2, :3, :4, :5, :6, :7)',
                    [
                        (
                            course.course_id,
                            course.name,
                            str(course.time),
                            str(course.score),
                            course.teacher,
                            course.location,
                            course.shared,
                        )
                        for course in data.courses
                    ],
                )
            if self._scalar(conn, "SELECT COUNT(1) FROM Enrollment") == 0:
                cursor.executemany(
                    'INSERT INTO Enrollment ("课程编号", "学号", "得分") VALUES (:1, :2, :3)',
                    [
                        (enrollment.course_id, enrollment.student_id, str(enrollment.score))
                        for enrollment in data.enrollments
                    ],
                )
            if self._scalar(conn, "SELECT COUNT(1) FROM EnrollmentLog") == 0:
                cursor.executemany(
                    """
                    INSERT INTO EnrollmentLog
                    (enrollment_id, student_id, course_id, source_college_id, target_college_id, score, origin, status, created_at, updated_at)
                    VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10)
                    """,
                    [
                        (
                            enrollment.enrollment_id,
                            enrollment.student_id,
                            enrollment.course_id,
                            enrollment.source_college_id,
                            enrollment.target_college_id,
                            enrollment.score,
                            enrollment.origin,
                            enrollment.status,
                            now,
                            now,
                        )
                        for enrollment in data.enrollments
                    ],
                )
            conn.commit()
        finally:
            conn.close()

    def _scalar(self, conn: oracledb.Connection, sql: str, **params: Any) -> Any:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return None if row is None else row[0]

    def _fetch_one(self, sql: str, **params: Any) -> tuple[Any, ...] | None:
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            row = cursor.fetchone()
            return tuple(row) if row else None
        finally:
            conn.close()

    def _fetch_all(self, sql: str, **params: Any) -> list[tuple[Any, ...]]:
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return [tuple(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def _execute(self, sql: str, **params: Any) -> None:
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
        finally:
            conn.close()

    def get_account(self, username: str) -> AccountRecord | None:
        row = self._fetch_one('SELECT "账户名", "密码", "级别", "客体" FROM Account WHERE "账户名" = :username', username=username)
        return None if row is None else AccountRecord(row[0], row[1], "ADMN" if int(row[2]) >= 9 else "STUD", row[3])

    def get_student(self, student_id: str) -> StudentRecord | None:
        row = self._fetch_one('SELECT "学号", "姓名", "性别", "专业" FROM Student WHERE "学号" = :student_id', student_id=student_id)
        return None if row is None else StudentRecord(row[0], row[1], row[2], row[3], "")

    def get_student_by_account(self, username: str) -> StudentRecord | None:
        account = self.get_account(username)
        return None if account is None or not account.student_id else self.get_student(account.student_id)

    def get_course(self, course_id: str) -> CourseRecord | None:
        row = self._fetch_one(
            'SELECT "编号", "名称", "课时", "学分", "老师", "地点", "共享" FROM Course WHERE "编号" = :course_id',
            course_id=course_id,
        )
        return self._course_from_row(row) if row else None

    def list_courses(self) -> list[CourseRecord]:
        rows = self._fetch_all('SELECT "编号", "名称", "课时", "学分", "老师", "地点", "共享" FROM Course ORDER BY "编号"')
        return [self._course_from_row(row) for row in rows]

    def list_shared_courses(self) -> list[CourseRecord]:
        rows = self._fetch_all(
            'SELECT "编号", "名称", "课时", "学分", "老师", "地点", "共享" FROM Course WHERE "共享" = :shared ORDER BY "编号"',
            shared="Y",
        )
        return [self._course_from_row(row) for row in rows]

    def get_stats_summary(self) -> dict[str, int | str]:
        conn = self._connect()
        try:
            return {
                "collegeId": self.college_id,
                "studentCount": int(self._scalar(conn, 'SELECT COUNT(1) FROM Student WHERE "学号" LIKE :prefix', prefix=f"{self.college_id}2024%") or 0),
                "courseCount": int(self._scalar(conn, "SELECT COUNT(1) FROM Course") or 0),
                "enrollmentCount": int(self._scalar(conn, "SELECT COUNT(1) FROM Enrollment") or 0),
                "sharedCourseCount": int(self._scalar(conn, 'SELECT COUNT(1) FROM Course WHERE "共享" = :shared', shared="Y") or 0),
            }
        finally:
            conn.close()

    def _ensure_inbound_student(self, student_id: str, source_college_id: str) -> StudentRecord | None:
        student = self.get_student(student_id)
        if student is not None:
            return student
        if source_college_id.upper() == self.college_id.upper():
            return None
        account = f"x{student_id[-8:]}"[:12]
        conn = self._connect()
        try:
            cursor = conn.cursor()
            if self._scalar(conn, 'SELECT COUNT(1) FROM Account WHERE "账户名" = :username', username=account) == 0:
                cursor.execute(
                    'INSERT INTO Account ("账户名", "密码", "级别", "客体") VALUES (:1, :2, :3, :4)',
                    (account, "123456", 1, student_id),
                )
            cursor.execute(
                'INSERT INTO Student ("学号", "姓名", "性别", "专业", "密码") VALUES (:1, :2, :3, :4, :5)',
                (student_id, f"外院{student_id[-6:]}", "未知", f"{source_college_id.upper()}学院", "123456"),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_student(student_id)

    def _course_from_row(self, row: tuple[Any, ...]) -> CourseRecord:
        return CourseRecord(row[0], row[1], int(row[2]), int(row[3]), row[4], row[5], row[6], 999)

    def get_enrollment(self, enrollment_id: str) -> EnrollmentRecord | None:
        row = self._fetch_one(
            """
            SELECT enrollment_id, student_id, course_id, score, source_college_id, target_college_id, origin, status
            FROM EnrollmentLog WHERE enrollment_id = :enrollment_id
            """,
            enrollment_id=enrollment_id,
        )
        return self._enrollment_from_row(row) if row else None

    def get_enrollment_by_pair(self, student_id: str, course_id: str) -> EnrollmentRecord | None:
        row = self._fetch_one(
            """
            SELECT enrollment_id, student_id, course_id, score, source_college_id, target_college_id, origin, status
            FROM EnrollmentLog
            WHERE student_id = :student_id AND course_id = :course_id AND status = 'ENROLLED'
            FETCH FIRST 1 ROWS ONLY
            """,
            student_id=student_id,
            course_id=course_id,
        )
        return self._enrollment_from_row(row) if row else None

    def _enrollment_from_row(self, row: tuple[Any, ...]) -> EnrollmentRecord:
        return EnrollmentRecord(row[0], row[1], row[2], int(row[3]), row[4], row[5], row[6], row[7])

    def get_outbound_request(self, enrollment_id: str) -> dict[str, Any] | None:
        row = self._fetch_one(
            """
            SELECT enrollment_id, home_college_id, target_college_id, student_id, course_id, score, status, request_time, updated_at
            FROM OutboundRequestLog WHERE enrollment_id = :enrollment_id
            """,
            enrollment_id=enrollment_id,
        )
        if row is None:
            return None
        return {
            "enrollmentId": row[0],
            "homeCollegeId": row[1],
            "targetCollegeId": row[2],
            "studentId": row[3],
            "courseId": row[4],
            "score": int(row[5]),
            "status": row[6],
            "requestTime": row[7],
            "updatedAt": row[8],
        }

    def _active_course_count(self, course_id: str) -> int:
        row = self._fetch_one('SELECT COUNT(1) FROM Enrollment WHERE "课程编号" = :course_id', course_id=course_id)
        return int(row[0]) if row else 0

    def _next_enrollment_id(self) -> str:
        return f"E{_utc_now().strftime('%Y%m%d')}{next(self._enrollment_seq):04d}"

    def create_local_enrollment(self, student_id: str, course_id: str, score: int = 0) -> tuple[EnrollmentRecord, bool]:
        student = self._ensure_inbound_student(student_id, source_college_id)
        course = self.get_course(course_id)
        if student is None:
            raise NotFoundError("student not found")
        if course is None:
            raise NotFoundError("course not found")
        existing = self.get_enrollment_by_pair(student_id, course_id)
        if existing is not None and existing.status == "ENROLLED":
            return existing, False
        if self._active_course_count(course_id) >= course.capacity:
            raise CourseFullError("course is full")
        enrollment_id = self._next_enrollment_id()
        now = _utc_now().replace(tzinfo=None)
        self._execute('INSERT INTO Enrollment ("课程编号", "学号", "得分") VALUES (:course_id, :student_id, :score)', course_id=course_id, student_id=student_id, score=str(score))
        self._insert_enrollment_log(enrollment_id, student_id, course_id, self.college_id, self.college_id, score, "LOCAL", "ENROLLED", now)
        return self.get_enrollment(enrollment_id), True

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
        existing = self.get_enrollment_by_pair(student_id, course_id)
        if existing is not None and existing.status == "ENROLLED":
            return existing, False
        if self._active_course_count(course_id) >= course.capacity:
            raise CourseFullError("course is full")
        enrollment_id = enrollment_id or self._next_enrollment_id()
        now = _utc_now().replace(tzinfo=None)
        self._execute('INSERT INTO Enrollment ("课程编号", "学号", "得分") VALUES (:course_id, :student_id, :score)', course_id=course_id, student_id=student_id, score=str(score))
        self._insert_enrollment_log(enrollment_id, student_id, course_id, source_college_id, target_college_id, score, "INBOUND", status, now)
        return self.get_enrollment(enrollment_id), True

    def _insert_enrollment_log(
        self,
        enrollment_id: str,
        student_id: str,
        course_id: str,
        source_college_id: str,
        target_college_id: str,
        score: int,
        origin: str,
        status: str,
        now: datetime,
    ) -> None:
        self._execute(
            """
            INSERT INTO EnrollmentLog
            (enrollment_id, student_id, course_id, source_college_id, target_college_id, score, origin, status, created_at, updated_at)
            VALUES (:enrollment_id, :student_id, :course_id, :source_college_id, :target_college_id, :score, :origin, :status, :created_at, :updated_at)
            """,
            enrollment_id=enrollment_id,
            student_id=student_id,
            course_id=course_id,
            source_college_id=source_college_id,
            target_college_id=target_college_id,
            score=score,
            origin=origin,
            status=status,
            created_at=now,
            updated_at=now,
        )

    def withdraw_enrollment(self, *, enrollment_id: str, student_id: str | None = None, course_id: str | None = None) -> tuple[EnrollmentRecord, bool]:
        record = self.get_enrollment(enrollment_id)
        if record is None and student_id and course_id:
            record = self.get_enrollment_by_pair(student_id, course_id)
        if record is None:
            raise NotFoundError("enrollment not found")
        if record.status == "WITHDRAWN":
            return record, False
        self._execute('DELETE FROM Enrollment WHERE "学号" = :student_id AND "课程编号" = :course_id', student_id=record.student_id, course_id=record.course_id)
        self._execute(
            "UPDATE EnrollmentLog SET status = :status, updated_at = :updated_at WHERE enrollment_id = :enrollment_id",
            status="WITHDRAWN",
            updated_at=_utc_now().replace(tzinfo=None),
            enrollment_id=record.enrollment_id,
        )
        updated = self.get_enrollment(record.enrollment_id)
        return updated or record, True

    def register_outbound_request(self, *, home_college_id: str, target_college_id: str, student_id: str, course_id: str, score: int) -> str:
        enrollment_id = self._next_enrollment_id()
        now = _utc_now().strftime("%Y-%m-%d %H:%M:%S")
        self._execute(
            """
            INSERT INTO OutboundRequestLog
            (enrollment_id, home_college_id, target_college_id, student_id, course_id, score, status, request_time, updated_at)
            VALUES (:enrollment_id, :home_college_id, :target_college_id, :student_id, :course_id, :score, :status, :request_time, :updated_at)
            """,
            enrollment_id=enrollment_id,
            home_college_id=home_college_id,
            target_college_id=target_college_id,
            student_id=student_id,
            course_id=course_id,
            score=score,
            status="PENDING_WRITEBACK",
            request_time=now,
            updated_at=None,
        )
        return enrollment_id

    def withdraw_outbound_request(self, enrollment_id: str) -> dict[str, Any]:
        request = self.get_outbound_request(enrollment_id)
        if request is None:
            raise NotFoundError("enrollment not found")
        if request["status"] == "WITHDRAWN":
            return request
        now = _utc_now().strftime("%Y-%m-%d %H:%M:%S")
        self._execute(
            "UPDATE OutboundRequestLog SET status = :status, updated_at = :updated_at WHERE enrollment_id = :enrollment_id",
            status="WITHDRAWN",
            updated_at=now,
            enrollment_id=enrollment_id,
        )
        request["status"] = "WITHDRAWN"
        request["updatedAt"] = now
        return request

    def courses_to_dicts(self, courses: list[CourseRecord]) -> list[dict[str, Any]]:
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

    def students_to_dicts(self, students: list[StudentRecord]) -> list[dict[str, Any]]:
        return [
            {"id": student.student_id, "name": student.name, "major": student.major, "gender": student.gender}
            for student in students
        ]

    def enrollment_to_dict(self, record: EnrollmentRecord) -> dict[str, Any]:
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
