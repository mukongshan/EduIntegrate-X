from __future__ import annotations

from datetime import datetime, timezone
from itertools import count
from typing import Any

import pyodbc

from .models import AccountRecord, CourseRecord, EnrollmentRecord, StudentRecord
from .repository import CourseFullError, NotFoundError, ValidationError


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SqlServerCollegeARepository:
    def __init__(
        self,
        *,
        server: str,
        database: str,
        driver: str = "ODBC Driver 18 for SQL Server",
        trusted_connection: bool = True,
        user: str = "",
        password: str = "",
        college_id: str = "A",
        init_schema: bool = True,
        reset_data: bool = False,
    ) -> None:
        self.server = server
        self.database = database
        self.driver = driver
        self.trusted_connection = trusted_connection
        self.user = user
        self.password = password
        self.college_id = college_id
        self._enrollment_seq = count(1)
        self._ensure_database()
        if init_schema:
            self._ensure_schema()
        if reset_data:
            self.reset_demo_data()
        else:
            self.seed_demo_data()

    def _connection_string(self, database: str | None = None) -> str:
        parts = [f"DRIVER={{{self.driver}}}", f"SERVER={self.server}"]
        if database is not None:
            parts.append(f"DATABASE={database}")
        if self.trusted_connection:
            parts.append("Trusted_Connection=yes")
        else:
            parts.append(f"UID={self.user}")
            parts.append(f"PWD={self.password}")
        parts.append("TrustServerCertificate=yes")
        parts.append("Encrypt=no")
        return ";".join(parts) + ";"

    def _connect(self, database: str | None = None) -> pyodbc.Connection:
        return pyodbc.connect(self._connection_string(database), autocommit=False)

    def _ensure_database(self) -> None:
        try:
            probe = self._connect(self.database)
            probe.close()
            return
        except pyodbc.Error:
            pass
        master = self._connect("master")
        try:
            cursor = master.cursor()
            cursor.execute(
                """
                IF DB_ID(?) IS NULL
                BEGIN
                    DECLARE @sql nvarchar(max) = N'CREATE DATABASE [' + REPLACE(?, ']', ']]') + N']';
                    EXEC sp_executesql @sql;
                END
                """,
                self.database,
                self.database,
            )
            master.commit()
        finally:
            master.close()

    def _ensure_schema(self) -> None:
        conn = self._connect(self.database)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                IF OBJECT_ID(N'[dbo].[Account]', N'U') IS NULL
                BEGIN
                    CREATE TABLE [dbo].[Account] (
                        [账户名] varchar(10) NOT NULL PRIMARY KEY,
                        [密码] varchar(6) NOT NULL,
                        [权限] char(4) NOT NULL
                    );
                END
                """
            )
            cursor.execute(
                """
                IF OBJECT_ID(N'[dbo].[Student]', N'U') IS NULL
                BEGIN
                    CREATE TABLE [dbo].[Student] (
                        [学号] varchar(12) NOT NULL PRIMARY KEY,
                        [姓名] varchar(10) NOT NULL,
                        [性别] varchar(2) NOT NULL,
                        [院系] varchar(10) NOT NULL,
                        [关联账户] varchar(10) NOT NULL,
                        CONSTRAINT [FK_Student_Account] FOREIGN KEY ([关联账户]) REFERENCES [dbo].[Account]([账户名])
                    );
                END
                """
            )
            cursor.execute(
                """
                IF OBJECT_ID(N'[dbo].[Course]', N'U') IS NULL
                BEGIN
                    CREATE TABLE [dbo].[Course] (
                        [课程编号] varchar(8) NOT NULL PRIMARY KEY,
                        [课程名称] varchar(10) NOT NULL,
                        [学分] varchar(2) NOT NULL,
                        [授课老师] varchar(10) NOT NULL,
                        [授课地点] varchar(20) NOT NULL,
                        [共享] char(1) NOT NULL
                    );
                END
                """
            )
            cursor.execute(
                """
                IF OBJECT_ID(N'[dbo].[Enrollment]', N'U') IS NULL
                BEGIN
                    CREATE TABLE [dbo].[Enrollment] (
                        [课程编号] varchar(8) NOT NULL,
                        [学生编号] varchar(12) NOT NULL,
                        [成绩] varchar(3) NOT NULL,
                        CONSTRAINT [UQ_Enrollment_CourseStudent] UNIQUE ([课程编号], [学生编号]),
                        CONSTRAINT [FK_Enrollment_Course] FOREIGN KEY ([课程编号]) REFERENCES [dbo].[Course]([课程编号]),
                        CONSTRAINT [FK_Enrollment_Student] FOREIGN KEY ([学生编号]) REFERENCES [dbo].[Student]([学号])
                    );
                END
                """
            )
            cursor.execute(
                """
                IF OBJECT_ID(N'[dbo].[EnrollmentLog]', N'U') IS NULL
                BEGIN
                    CREATE TABLE [dbo].[EnrollmentLog] (
                        [enrollment_id] varchar(20) NOT NULL PRIMARY KEY,
                        [student_id] varchar(12) NOT NULL,
                        [course_id] varchar(8) NOT NULL,
                        [source_college_id] varchar(8) NOT NULL,
                        [target_college_id] varchar(8) NOT NULL,
                        [score] int NOT NULL,
                        [origin] varchar(16) NOT NULL,
                        [status] varchar(16) NOT NULL,
                        [created_at] datetime2 NOT NULL,
                        [updated_at] datetime2 NOT NULL
                    );
                END
                """
            )
            cursor.execute(
                """
                IF OBJECT_ID(N'[dbo].[OutboundRequestLog]', N'U') IS NULL
                BEGIN
                    CREATE TABLE [dbo].[OutboundRequestLog] (
                        [enrollment_id] varchar(20) NOT NULL PRIMARY KEY,
                        [home_college_id] varchar(8) NOT NULL,
                        [target_college_id] varchar(8) NOT NULL,
                        [student_id] varchar(12) NOT NULL,
                        [course_id] varchar(8) NOT NULL,
                        [score] int NOT NULL,
                        [status] varchar(20) NOT NULL,
                        [request_time] varchar(19) NOT NULL,
                        [updated_at] varchar(19) NULL
                    );
                END
                """
            )
            conn.commit()
        finally:
            conn.close()

    def reset_demo_data(self) -> None:
        conn = self._connect(self.database)
        try:
            cursor = conn.cursor()
            cursor.execute("ALTER TABLE [dbo].[Enrollment] NOCHECK CONSTRAINT ALL;")
            cursor.execute("ALTER TABLE [dbo].[Student] NOCHECK CONSTRAINT ALL;")
            cursor.execute("DELETE FROM [dbo].[OutboundRequestLog];")
            cursor.execute("DELETE FROM [dbo].[EnrollmentLog];")
            cursor.execute("DELETE FROM [dbo].[Enrollment];")
            cursor.execute("DELETE FROM [dbo].[Student];")
            cursor.execute("DELETE FROM [dbo].[Course];")
            cursor.execute("DELETE FROM [dbo].[Account];")
            cursor.execute("ALTER TABLE [dbo].[Student] WITH CHECK CHECK CONSTRAINT ALL;")
            cursor.execute("ALTER TABLE [dbo].[Enrollment] WITH CHECK CHECK CONSTRAINT ALL;")
            conn.commit()
        finally:
            conn.close()
        self.seed_demo_data()

    def seed_demo_data(self) -> None:
        conn = self._connect(self.database)
        try:
            cursor = conn.cursor()
            if self._scalar(conn, "SELECT COUNT(1) FROM [dbo].[Account]") == 0:
                cursor.executemany(
                    "INSERT INTO [dbo].[Account] ([账户名], [密码], [权限]) VALUES (?, ?, ?)",
                    [
                        ("a_student1", "123456", "STUD"),
                        ("a_student2", "123456", "STUD"),
                        ("a_admin", "admin1", "ADMN"),
                    ],
                )
            if self._scalar(conn, "SELECT COUNT(1) FROM [dbo].[Student]") == 0:
                cursor.executemany(
                    "INSERT INTO [dbo].[Student] ([学号], [姓名], [性别], [院系], [关联账户]) VALUES (?, ?, ?, ?, ?)",
                    [
                        ("S2024001", "张小明", "男", "计算机", "a_student1"),
                        ("S2024002", "李小红", "女", "软件工程", "a_student2"),
                        ("S2024003", "王小林", "男", "数据科学", "a_student1"),
                    ],
                )
            if self._scalar(conn, "SELECT COUNT(1) FROM [dbo].[Course]") == 0:
                cursor.executemany(
                    "INSERT INTO [dbo].[Course] ([课程编号], [课程名称], [学分], [授课老师], [授课地点], [共享]) VALUES (?, ?, ?, ?, ?, ?)",
                    [
                        ("A001", "数据库系统", "3", "张老师", "1-301", "Y"),
                        ("A002", "Java设计", "4", "李老师", "2-201", "N"),
                        ("A003", "数仓基础", "2", "王老师", "3-105", "Y"),
                    ],
                )
            conn.commit()
        finally:
            conn.close()

    def _scalar(self, conn: pyodbc.Connection, sql: str, *params: Any) -> Any:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return None if row is None else row[0]

    def _fetch_one(self, sql: str, *params: Any) -> tuple[Any, ...] | None:
        conn = self._connect(self.database)
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            row = cursor.fetchone()
            return tuple(row) if row else None
        finally:
            conn.close()

    def _fetch_all(self, sql: str, *params: Any) -> list[tuple[Any, ...]]:
        conn = self._connect(self.database)
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [tuple(row) for row in rows]
        finally:
            conn.close()

    def _execute(self, sql: str, *params: Any) -> None:
        conn = self._connect(self.database)
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
        finally:
            conn.close()

    def get_account(self, username: str) -> AccountRecord | None:
        row = self._fetch_one(
            "SELECT [账户名], [密码], [权限] FROM [dbo].[Account] WHERE [账户名] = ?",
            username,
        )
        return None if row is None else AccountRecord(row[0], row[1], row[2])

    def get_student(self, student_id: str) -> StudentRecord | None:
        row = self._fetch_one(
            "SELECT [学号], [姓名], [性别], [院系], [关联账户] FROM [dbo].[Student] WHERE [学号] = ?",
            student_id,
        )
        return None if row is None else StudentRecord(row[0], row[1], row[2], row[3], row[4])

    def get_student_by_account(self, username: str) -> StudentRecord | None:
        row = self._fetch_one(
            "SELECT [学号], [姓名], [性别], [院系], [关联账户] FROM [dbo].[Student] WHERE [关联账户] = ?",
            username,
        )
        return None if row is None else StudentRecord(row[0], row[1], row[2], row[3], row[4])

    def get_course(self, course_id: str) -> CourseRecord | None:
        row = self._fetch_one(
            "SELECT [课程编号], [课程名称], [学分], [授课老师], [授课地点], [共享] FROM [dbo].[Course] WHERE [课程编号] = ?",
            course_id,
        )
        if row is None:
            return None
        return CourseRecord(
            course_id=row[0],
            name=row[1],
            time=0,
            score=int(row[2]),
            teacher=row[3],
            location=row[4],
            shared=row[5],
            capacity=999,
        )

    def list_courses(self) -> list[CourseRecord]:
        rows = self._fetch_all(
            "SELECT [课程编号], [课程名称], [学分], [授课老师], [授课地点], [共享] FROM [dbo].[Course] ORDER BY [课程编号]"
        )
        return [
            CourseRecord(
                course_id=row[0],
                name=row[1],
                time=0,
                score=int(row[2]),
                teacher=row[3],
                location=row[4],
                shared=row[5],
                capacity=999,
            )
            for row in rows
        ]

    def list_shared_courses(self) -> list[CourseRecord]:
        rows = self._fetch_all(
            "SELECT [课程编号], [课程名称], [学分], [授课老师], [授课地点], [共享] FROM [dbo].[Course] WHERE [共享] = 'Y' ORDER BY [课程编号]"
        )
        return [
            CourseRecord(
                course_id=row[0],
                name=row[1],
                time=0,
                score=int(row[2]),
                teacher=row[3],
                location=row[4],
                shared=row[5],
                capacity=999,
            )
            for row in rows
        ]

    def get_enrollment(self, enrollment_id: str) -> EnrollmentRecord | None:
        row = self._fetch_one(
            """
            SELECT [enrollment_id], [student_id], [course_id], [score], [source_college_id], [target_college_id], [origin], [status]
            FROM [dbo].[EnrollmentLog]
            WHERE [enrollment_id] = ?
            """,
            enrollment_id,
        )
        if row is None:
            return None
        return EnrollmentRecord(
            enrollment_id=row[0],
            student_id=row[1],
            course_id=row[2],
            score=int(row[3]),
            source_college_id=row[4],
            target_college_id=row[5],
            origin=row[6],
            status=row[7],
        )

    def get_outbound_request(self, enrollment_id: str) -> dict[str, Any] | None:
        row = self._fetch_one(
            """
            SELECT [enrollment_id], [home_college_id], [target_college_id], [student_id], [course_id], [score], [status], [request_time], [updated_at]
            FROM [dbo].[OutboundRequestLog]
            WHERE [enrollment_id] = ?
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
        row = self._fetch_one(
            "SELECT 1 FROM [dbo].[Enrollment] WHERE [学生编号] = ? AND [课程编号] = ?",
            student_id,
            course_id,
        )
        return row is not None

    def _active_course_count(self, course_id: str) -> int:
        row = self._fetch_one(
            "SELECT COUNT(1) FROM [dbo].[Enrollment] WHERE [课程编号] = ?",
            course_id,
        )
        return int(row[0]) if row else 0

    def _next_enrollment_id(self) -> str:
        return f"E{_utc_now().strftime('%Y%m%d')}{next(self._enrollment_seq):04d}"

    def get_enrollment_by_pair(self, student_id: str, course_id: str) -> EnrollmentRecord | None:
        row = self._fetch_one(
            """
            SELECT TOP 1 [enrollment_id], [student_id], [course_id], [score], [source_college_id], [target_college_id], [origin], [status]
            FROM [dbo].[EnrollmentLog]
            WHERE [student_id] = ? AND [course_id] = ? AND [status] = 'ENROLLED'
            ORDER BY [created_at] DESC
            """,
            student_id,
            course_id,
        )
        if row is None:
            return None
        return EnrollmentRecord(
            enrollment_id=row[0],
            student_id=row[1],
            course_id=row[2],
            score=int(row[3]),
            source_college_id=row[4],
            target_college_id=row[5],
            origin=row[6],
            status=row[7],
        )

    def create_local_enrollment(self, student_id: str, course_id: str, score: int = 0) -> tuple[EnrollmentRecord, bool]:
        student = self.get_student(student_id)
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
        self._execute(
            "INSERT INTO [dbo].[Enrollment] ([课程编号], [学生编号], [成绩]) VALUES (?, ?, ?)",
            course_id,
            student_id,
            str(score),
        )
        self._execute(
            """
            INSERT INTO [dbo].[EnrollmentLog]
            ([enrollment_id], [student_id], [course_id], [source_college_id], [target_college_id], [score], [origin], [status], [created_at], [updated_at])
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        self._execute(
            "INSERT INTO [dbo].[Enrollment] ([课程编号], [学生编号], [成绩]) VALUES (?, ?, ?)",
            course_id,
            student_id,
            str(score),
        )
        self._execute(
            """
            INSERT INTO [dbo].[EnrollmentLog]
            ([enrollment_id], [student_id], [course_id], [source_college_id], [target_college_id], [score], [origin], [status], [created_at], [updated_at])
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        self._execute(
            "DELETE FROM [dbo].[Enrollment] WHERE [学生编号] = ? AND [课程编号] = ?",
            record.student_id,
            record.course_id,
        )
        self._execute(
            "UPDATE [dbo].[EnrollmentLog] SET [status] = ?, [updated_at] = ? WHERE [enrollment_id] = ?",
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
            INSERT INTO [dbo].[OutboundRequestLog]
            ([enrollment_id], [home_college_id], [target_college_id], [student_id], [course_id], [score], [status], [request_time], [updated_at])
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            "UPDATE [dbo].[OutboundRequestLog] SET [status] = ?, [updated_at] = ? WHERE [enrollment_id] = ?",
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
        return [
            {
                "id": student.student_id,
                "name": student.name,
                "major": student.major,
                "gender": student.gender,
            }
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
