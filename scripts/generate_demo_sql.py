#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from demo_data import CollegeDemoData, generate_college_demo_data

OUT_DIR = ROOT_DIR / "data" / "generated"
FIXED_TIME = "2026-05-28 00:00:00"


def quote(value: object) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def nquote(value: object) -> str:
    if value is None:
        return "NULL"
    return "N" + quote(value)


def sql_server_timestamp() -> str:
    return f"CONVERT(datetime2, {quote(FIXED_TIME)}, 120)"


def oracle_timestamp() -> str:
    return f"TO_TIMESTAMP({quote(FIXED_TIME)}, 'YYYY-MM-DD HH24:MI:SS')"


def build_sql_server(data: CollegeDemoData) -> str:
    lines = [
        "-- College A demo data for SQL Server",
        "-- Assumes the schema created by college_a/app/sqlserver_repository.py already exists.",
        "DELETE FROM [dbo].[OutboundRequestLog];",
        "DELETE FROM [dbo].[EnrollmentLog];",
        "DELETE FROM [dbo].[Enrollment];",
        "DELETE FROM [dbo].[Student];",
        "DELETE FROM [dbo].[Course];",
        "DELETE FROM [dbo].[Account];",
        "GO",
        "",
    ]
    for account in data.accounts:
        lines.append(
            "INSERT INTO [dbo].[Account] ([账户名], [密码], [权限]) VALUES "
            f"({nquote(account.username)}, {nquote(account.password)}, {nquote(account.role)});"
        )
    lines.append("")
    for student in data.students:
        lines.append(
            "INSERT INTO [dbo].[Student] ([学号], [姓名], [性别], [院系], [关联账户]) VALUES "
            f"({nquote(student.student_id)}, {nquote(student.name)}, {nquote(student.gender)}, "
            f"{nquote(student.major)}, {nquote(student.account_username)});"
        )
    lines.append("")
    for course in data.courses:
        lines.append(
            "INSERT INTO [dbo].[Course] ([课程编号], [课程名称], [学分], [授课老师], [授课地点], [共享]) VALUES "
            f"({nquote(course.course_id)}, {nquote(course.name)}, {nquote(course.score)}, "
            f"{nquote(course.teacher)}, {nquote(course.location)}, {nquote(course.shared)});"
        )
    lines.append("")
    for enrollment in data.enrollments:
        lines.append(
            "INSERT INTO [dbo].[Enrollment] ([课程编号], [学生编号], [成绩]) VALUES "
            f"({nquote(enrollment.course_id)}, {nquote(enrollment.student_id)}, {nquote(enrollment.score)});"
        )
    lines.append("")
    for enrollment in data.enrollments:
        lines.append(
            "INSERT INTO [dbo].[EnrollmentLog] "
            "([enrollment_id], [student_id], [course_id], [source_college_id], [target_college_id], "
            "[score], [origin], [status], [created_at], [updated_at]) VALUES "
            f"({nquote(enrollment.enrollment_id)}, {nquote(enrollment.student_id)}, {nquote(enrollment.course_id)}, "
            f"{nquote(enrollment.source_college_id)}, {nquote(enrollment.target_college_id)}, {enrollment.score}, "
            f"{nquote(enrollment.origin)}, {nquote(enrollment.status)}, {sql_server_timestamp()}, {sql_server_timestamp()});"
        )
    lines.extend(["GO", ""])
    return "\n".join(lines)


def build_oracle(data: CollegeDemoData) -> str:
    lines = [
        "-- College B demo data for Oracle",
        "-- Assumes the schema created by college_b/app/oracle_repository.py already exists.",
        "DELETE FROM OutboundRequestLog;",
        "DELETE FROM EnrollmentLog;",
        "DELETE FROM Enrollment;",
        "DELETE FROM Course;",
        "DELETE FROM Account;",
        "DELETE FROM Student;",
        "",
    ]
    for account in data.accounts:
        level = 9 if account.role == "ADMN" else 1
        lines.append(
            'INSERT INTO Account ("账户名", "密码", "级别", "客体") VALUES '
            f"({quote(account.username)}, {quote(account.password)}, {level}, {quote(account.student_id)});"
        )
    lines.append("")
    for student in data.students:
        lines.append(
            'INSERT INTO Student ("学号", "姓名", "性别", "专业", "密码") VALUES '
            f"({quote(student.student_id)}, {quote(student.name)}, {quote(student.gender)}, "
            f"{quote(student.major)}, '123456');"
        )
    lines.append("")
    for course in data.courses:
        lines.append(
            'INSERT INTO Course ("编号", "名称", "课时", "学分", "老师", "地点", "共享") VALUES '
            f"({quote(course.course_id)}, {quote(course.name)}, {quote(course.time)}, {quote(course.score)}, "
            f"{quote(course.teacher)}, {quote(course.location)}, {quote(course.shared)});"
        )
    lines.append("")
    for enrollment in data.enrollments:
        lines.append(
            'INSERT INTO Enrollment ("课程编号", "学号", "得分") VALUES '
            f"({quote(enrollment.course_id)}, {quote(enrollment.student_id)}, {quote(enrollment.score)});"
        )
    lines.append("")
    for enrollment in data.enrollments:
        lines.append(
            "INSERT INTO EnrollmentLog "
            "(enrollment_id, student_id, course_id, source_college_id, target_college_id, "
            "score, origin, status, created_at, updated_at) VALUES "
            f"({quote(enrollment.enrollment_id)}, {quote(enrollment.student_id)}, {quote(enrollment.course_id)}, "
            f"{quote(enrollment.source_college_id)}, {quote(enrollment.target_college_id)}, {enrollment.score}, "
            f"{quote(enrollment.origin)}, {quote(enrollment.status)}, {oracle_timestamp()}, {oracle_timestamp()});"
        )
    lines.extend(["COMMIT;", ""])
    return "\n".join(lines)


def build_mysql(data: CollegeDemoData) -> str:
    lines = [
        "-- College C demo data for MySQL",
        "-- Assumes the schema created by college_c/app/mysql_repository.py already exists.",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "DELETE FROM OutboundRequestLog;",
        "DELETE FROM EnrollmentLog;",
        "DELETE FROM Enrollment;",
        "DELETE FROM Student;",
        "DELETE FROM Course;",
        "DELETE FROM Account;",
        "SET FOREIGN_KEY_CHECKS = 1;",
        "",
    ]
    for account in data.accounts:
        lines.append(f"INSERT INTO Account (acc, passwd) VALUES ({quote(account.username)}, {quote(account.password)});")
    lines.append("")
    for student in data.students:
        lines.append(
            "INSERT INTO Student (Sno, Snm, Sex, Sde, Pwd) VALUES "
            f"({quote(student.student_id)}, {quote(student.name)}, {quote(student.gender[:1])}, "
            f"{quote(student.major)}, '123456');"
        )
    lines.append("")
    for course in data.courses:
        lines.append(
            "INSERT INTO Course (Cno, Cnm, Ctm, Cpt, Tec, Pla, Share, capacity) VALUES "
            f"({quote(course.course_id)}, {quote(course.name)}, {course.time}, {course.score}, "
            f"{quote(course.teacher)}, {quote(course.location)}, {quote(course.shared)}, {course.capacity});"
        )
    lines.append("")
    for enrollment in data.enrollments:
        lines.append(
            "INSERT INTO Enrollment (Cno, Sno, Grd) VALUES "
            f"({quote(enrollment.course_id)}, {quote(enrollment.student_id)}, {enrollment.score});"
        )
    lines.append("")
    for enrollment in data.enrollments:
        lines.append(
            "INSERT INTO EnrollmentLog "
            "(enrollment_id, student_id, course_id, source_college_id, target_college_id, "
            "score, origin, status, created_at, updated_at) VALUES "
            f"({quote(enrollment.enrollment_id)}, {quote(enrollment.student_id)}, {quote(enrollment.course_id)}, "
            f"{quote(enrollment.source_college_id)}, {quote(enrollment.target_college_id)}, {enrollment.score}, "
            f"{quote(enrollment.origin)}, {quote(enrollment.status)}, {quote(FIXED_TIME)}, {quote(FIXED_TIME)});"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        OUT_DIR / "college_a_demo.sql": build_sql_server(generate_college_demo_data("A")),
        OUT_DIR / "college_b_demo.sql": build_oracle(generate_college_demo_data("B")),
        OUT_DIR / "college_c_demo.sql": build_mysql(generate_college_demo_data("C")),
    }
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
        data = generate_college_demo_data(path.stem.split("_")[1].upper())
        print(
            f"{path.relative_to(ROOT_DIR)}: "
            f"{len(data.students)} students, {len(data.courses)} courses, {len(data.enrollments)} enrollments"
        )


if __name__ == "__main__":
    main()
