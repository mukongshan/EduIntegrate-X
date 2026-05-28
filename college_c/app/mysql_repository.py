from __future__ import annotations

from datetime import datetime, timezone
from itertools import count
from typing import Any

try:
    import pymysql
except ImportError:  # pragma: no cover - exercised only when mysql mode is requested without dependency
    pymysql = None

from demo_data import generate_college_demo_data

from .models import AccountRecord, CourseRecord, EnrollmentRecord, StudentRecord
from .repository import CourseFullError, NotFoundError, ValidationError


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MySqlCollegeCRepository:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str = "",
        charset: str = "utf8mb4",
        college_id: str = "C",
        init_schema: bool = True,
        reset_data: bool = False,
    ) -> None:
        if pymysql is None:
            raise RuntimeError("pymysql is required for COLLEGE_C_STORAGE=mysql")
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.charset = charset
        self.college_id = college_id
        self._enrollment_seq = count(1)
        self._ensure_database()
        if init_schema:
            self._ensure_schema()
        if reset_data:
            self.reset_demo_data()
        else:
            self.seed_demo_data()

    def _connect(self, database: str | None = None):
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=database,
            charset=self.charset,
            autocommit=False,
            cursorclass=pymysql.cursors.Cursor,
        )

    def _ensure_database(self) -> None:
        conn = self._connect(None)
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{self.database}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            conn.commit()
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        conn = self._connect(self.database)
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS Account (
                        acc varchar(12) NOT NULL PRIMARY KEY,
                        passwd varchar(12) NOT NULL,
                        CreateDate timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS Student (
                        Sno varchar(9) NOT NULL PRIMARY KEY,
                        Snm varchar(10) NOT NULL,
                        Sex varchar(1) NOT NULL,
                        Sde varchar(6) NOT NULL,
                        Pwd char(6) NOT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS Course (
                        Cno char(4) NOT NULL PRIMARY KEY,
                        Cnm varchar(10) NOT NULL,
                        Ctm integer NOT NULL,
                        Cpt integer NOT NULL,
                        Tec varchar(20) NOT NULL,
                        Pla varchar(18) NOT NULL,
                        Share char(1) NOT NULL,
                        capacity integer NOT NULL DEFAULT 30
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS Enrollment (
                        Cno char(4) NOT NULL,
                        Sno varchar(9) NOT NULL,
                        Grd integer NOT NULL,
                        UNIQUE KEY uq_enrollment_course_student (Cno, Sno),
                        CONSTRAINT fk_enrollment_course FOREIGN KEY (Cno) REFERENCES Course(Cno),
                        CONSTRAINT fk_enrollment_student FOREIGN KEY (Sno) REFERENCES Student(Sno)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS EnrollmentLog (
                        enrollment_id varchar(20) NOT NULL PRIMARY KEY,
                        student_id varchar(9) NOT NULL,
                        course_id char(4) NOT NULL,
                        source_college_id varchar(8) NOT NULL,
                        target_college_id varchar(8) NOT NULL,
                        score integer NOT NULL,
                        origin varchar(16) NOT NULL,
                        status varchar(16) NOT NULL,
                        created_at datetime NOT NULL,
                        updated_at datetime NOT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS OutboundRequestLog (
                        enrollment_id varchar(20) NOT NULL PRIMARY KEY,
                        home_college_id varchar(8) NOT NULL,
                        target_college_id varchar(8) NOT NULL,
                        student_id varchar(9) NOT NULL,
                        course_id varchar(8) NOT NULL,
                        score integer NOT NULL,
                        status varchar(20) NOT NULL,
                        request_time varchar(19) NOT NULL,
                        updated_at varchar(19) NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                )
            conn.commit()
        finally:
            conn.close()

    def reset_demo_data(self) -> None:
        conn = self._connect(self.database)
        try:
            with conn.cursor() as cursor:
                cursor.execute("SET FOREIGN_KEY_CHECKS=0")
                for table in ("OutboundRequestLog", "EnrollmentLog", "Enrollment", "Student", "Course", "Account"):
                    cursor.execute(f"DELETE FROM {table}")
                cursor.execute("SET FOREIGN_KEY_CHECKS=1")
            conn.commit()
        finally:
            conn.close()
        self.seed_demo_data()

    def seed_demo_data(self) -> None:
        data = generate_college_demo_data(self.college_id)
        now = data.enrollments[0].created_at.replace(tzinfo=None) if data.enrollments else _utc_now().replace(tzinfo=None)
        conn = self._connect(self.database)
        try:
            with conn.cursor() as cursor:
                if self._scalar(conn, "SELECT COUNT(1) FROM Account") == 0:
                    cursor.executemany(
                        "INSERT INTO Account (acc, passwd) VALUES (%s, %s)",
                        [(account.username, account.password) for account in data.accounts],
                    )
                if self._scalar(conn, "SELECT COUNT(1) FROM Student") == 0:
                    cursor.executemany(
                        "INSERT INTO Student (Sno, Snm, Sex, Sde, Pwd) VALUES (%s, %s, %s, %s, %s)",
                        [
                            (student.student_id, student.name, student.gender[:1], student.major, "123456")
                            for student in data.students
                        ],
                    )
                if self._scalar(conn, "SELECT COUNT(1) FROM Course") == 0:
                    cursor.executemany(
                        "INSERT INTO Course (Cno, Cnm, Ctm, Cpt, Tec, Pla, Share, capacity) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        [
                            (
                                course.course_id,
                                course.name,
                                course.time,
                                course.score,
                                course.teacher,
                                course.location,
                                course.shared,
                                course.capacity,
                            )
                            for course in data.courses
                        ],
                    )
                if self._scalar(conn, "SELECT COUNT(1) FROM Enrollment") == 0:
                    cursor.executemany(
                        "INSERT INTO Enrollment (Cno, Sno, Grd) VALUES (%s, %s, %s)",
                        [
                            (enrollment.course_id, enrollment.student_id, enrollment.score)
                            for enrollment in data.enrollments
                        ],
                    )
                if self._scalar(conn, "SELECT COUNT(1) FROM EnrollmentLog") == 0:
                    cursor.executemany(
                        """
                        INSERT INTO EnrollmentLog
                        (enrollment_id, student_id, course_id, source_college_id, target_college_id, score, origin, status, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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

    def _scalar(self, conn, sql: str, *params: Any) -> Any:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            return None if row is None else row[0]

    def _fetch_one(self, sql: str, *params: Any) -> tuple[Any, ...] | None:
        conn = self._connect(self.database)
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                row = cursor.fetchone()
                return tuple(row) if row else None
        finally:
            conn.close()

    def _fetch_all(self, sql: str, *params: Any) -> list[tuple[Any, ...]]:
        conn = self._connect(self.database)
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return [tuple(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def _execute(self, sql: str, *params: Any) -> None:
        conn = self._connect(self.database)
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
            conn.commit()
        finally:
            conn.close()

    def get_account(self, username: str) -> AccountRecord | None:
        row = self._fetch_one("SELECT acc, passwd FROM Account WHERE acc = %s", username)
        if row is None:
            return None
        role = "ADMN" if username.endswith("admin") else "STUD"
        student = self.get_student_by_account(username)
        return AccountRecord(row[0], row[1], role, student.student_id if student else None)

    def get_student(self, student_id: str) -> StudentRecord | None:
        row = self._fetch_one("SELECT Sno, Snm, Sex, Sde FROM Student WHERE Sno = %s", student_id)
        return None if row is None else StudentRecord(row[0], row[1], row[2], row[3], self._account_for_student_id(row[0]))

    def get_student_by_account(self, username: str) -> StudentRecord | None:
        if username == "c_admin":
            return None
        if username.startswith("c_student"):
            suffix = username.removeprefix("c_student")
        elif username.startswith("cstu"):
            suffix = username.removeprefix("cstu")
        else:
            return None
        try:
            index = int(suffix)
        except ValueError:
            return None
        return self.get_student(f"C2024{index:03d}")

    def _account_for_student_id(self, student_id: str) -> str:
        try:
            index = int(student_id[-3:])
        except ValueError:
            return f"external_{student_id.lower()}"
        if index <= 2:
            return f"c_student{index}"
        return f"cstu{index:03d}"

    def get_course(self, course_id: str) -> CourseRecord | None:
        row = self._fetch_one("SELECT Cno, Cnm, Ctm, Cpt, Tec, Pla, Share, capacity FROM Course WHERE Cno = %s", course_id)
        if row is None:
            return None
        return CourseRecord(row[0], row[1], int(row[2]), int(row[3]), row[4], row[5], row[6], int(row[7]))

    def list_courses(self) -> list[CourseRecord]:
        rows = self._fetch_all("SELECT Cno, Cnm, Ctm, Cpt, Tec, Pla, Share, capacity FROM Course ORDER BY Cno")
        return [CourseRecord(row[0], row[1], int(row[2]), int(row[3]), row[4], row[5], row[6], int(row[7])) for row in rows]

    def list_shared_courses(self) -> list[CourseRecord]:
        rows = self._fetch_all("SELECT Cno, Cnm, Ctm, Cpt, Tec, Pla, Share, capacity FROM Course WHERE Share = 'Y' ORDER BY Cno")
        return [CourseRecord(row[0], row[1], int(row[2]), int(row[3]), row[4], row[5], row[6], int(row[7])) for row in rows]

    def get_stats_summary(self) -> dict[str, int | str]:
        conn = self._connect(self.database)
        try:
            return {
                "collegeId": self.college_id,
                "studentCount": int(self._scalar(conn, "SELECT COUNT(1) FROM Student WHERE Sno LIKE %s", f"{self.college_id}2024%") or 0),
                "courseCount": int(self._scalar(conn, "SELECT COUNT(1) FROM Course") or 0),
                "enrollmentCount": int(self._scalar(conn, "SELECT COUNT(1) FROM Enrollment") or 0),
                "sharedCourseCount": int(self._scalar(conn, "SELECT COUNT(1) FROM Course WHERE Share = 'Y'") or 0),
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
        conn = self._connect(self.database)
        try:
            with conn.cursor() as cursor:
                if self._scalar(conn, "SELECT COUNT(1) FROM Account WHERE acc = %s", account) == 0:
                    cursor.execute("INSERT INTO Account (acc, passwd) VALUES (%s, %s)", (account, "123456"))
                cursor.execute(
                    "INSERT INTO Student (Sno, Snm, Sex, Sde, Pwd) VALUES (%s, %s, %s, %s, %s)",
                    (student_id, f"外院{student_id[-6:]}", "外", f"{source_college_id.upper()}院", "123456"),
                )
            conn.commit()
        finally:
            conn.close()
        return self.get_student(student_id)

    def get_enrollment(self, enrollment_id: str) -> EnrollmentRecord | None:
        row = self._fetch_one(
            """
            SELECT enrollment_id, student_id, course_id, score, source_college_id, target_college_id, origin, status
            FROM EnrollmentLog
            WHERE enrollment_id = %s
            """,
            enrollment_id,
        )
        if row is None:
            return None
        return EnrollmentRecord(row[0], row[1], row[2], int(row[3]), row[4], row[5], row[6], row[7])

    def get_outbound_request(self, enrollment_id: str) -> dict[str, Any] | None:
        row = self._fetch_one(
            """
            SELECT enrollment_id, home_college_id, target_college_id, student_id, course_id, score, status, request_time, updated_at
            FROM OutboundRequestLog
            WHERE enrollment_id = %s
            """,
            enrollment_id,
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

    def _active_enrollment_exists(self, student_id: str, course_id: str) -> bool:
        return self._fetch_one("SELECT 1 FROM Enrollment WHERE Sno = %s AND Cno = %s", student_id, course_id) is not None

    def _active_course_count(self, course_id: str) -> int:
        row = self._fetch_one("SELECT COUNT(1) FROM Enrollment WHERE Cno = %s", course_id)
        return int(row[0]) if row else 0

    def _next_enrollment_id(self) -> str:
        return f"E{_utc_now().strftime('%Y%m%d')}{next(self._enrollment_seq):04d}"

    def get_enrollment_by_pair(self, student_id: str, course_id: str) -> EnrollmentRecord | None:
        row = self._fetch_one(
            """
            SELECT enrollment_id, student_id, course_id, score, source_college_id, target_college_id, origin, status
            FROM EnrollmentLog
            WHERE student_id = %s AND course_id = %s AND status = 'ENROLLED'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            student_id,
            course_id,
        )
        if row is None:
            return None
        return EnrollmentRecord(row[0], row[1], row[2], int(row[3]), row[4], row[5], row[6], row[7])

    def create_local_enrollment(self, student_id: str, course_id: str, score: int = 0) -> tuple[EnrollmentRecord, bool]:
        student = self._ensure_inbound_student(student_id, source_college_id)
        course = self.get_course(course_id)
        if student is None:
            raise NotFoundError("student not found")
        if course is None:
            raise NotFoundError("course not found")
        if self._active_enrollment_exists(student_id, course_id):
            existing = self.get_enrollment_by_pair(student_id, course_id)
            if existing is not None and existing.status == "ENROLLED":
                return existing, False
        if self._active_course_count(course_id) >= course.capacity:
            raise CourseFullError("course is full")
        enrollment_id = self._next_enrollment_id()
        now = _utc_now().replace(tzinfo=None)
        self._execute("INSERT INTO Enrollment (Cno, Sno, Grd) VALUES (%s, %s, %s)", course_id, student_id, score)
        self._execute(
            """
            INSERT INTO EnrollmentLog
            (enrollment_id, student_id, course_id, source_college_id, target_college_id, score, origin, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            enrollment_id,
            student_id,
            course_id,
            self.college_id,
            self.college_id,
            score,
            "LOCAL",
            "ENROLLED",
            now,
            now,
        )
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
        self._execute("INSERT INTO Enrollment (Cno, Sno, Grd) VALUES (%s, %s, %s)", course_id, student_id, score)
        self._execute(
            """
            INSERT INTO EnrollmentLog
            (enrollment_id, student_id, course_id, source_college_id, target_college_id, score, origin, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            enrollment_id,
            student_id,
            course_id,
            source_college_id,
            target_college_id,
            score,
            "INBOUND",
            status,
            now,
            now,
        )
        return self.get_enrollment(enrollment_id), True

    def withdraw_enrollment(
        self,
        *,
        enrollment_id: str,
        student_id: str | None = None,
        course_id: str | None = None,
    ) -> tuple[EnrollmentRecord, bool]:
        record = self.get_enrollment(enrollment_id)
        if record is None and student_id and course_id:
            record = self.get_enrollment_by_pair(student_id, course_id)
        if record is None:
            raise NotFoundError("enrollment not found")
        if record.status == "WITHDRAWN":
            return record, False
        self._execute("DELETE FROM Enrollment WHERE Sno = %s AND Cno = %s", record.student_id, record.course_id)
        self._execute(
            "UPDATE EnrollmentLog SET status = %s, updated_at = %s WHERE enrollment_id = %s",
            "WITHDRAWN",
            _utc_now().replace(tzinfo=None),
            record.enrollment_id,
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            enrollment_id,
            home_college_id,
            target_college_id,
            student_id,
            course_id,
            score,
            "PENDING_WRITEBACK",
            now,
            None,
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
            "UPDATE OutboundRequestLog SET status = %s, updated_at = %s WHERE enrollment_id = %s",
            "WITHDRAWN",
            now,
            enrollment_id,
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
        return [{"id": student.student_id, "name": student.name, "major": student.major, "gender": student.gender} for student in students]

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
