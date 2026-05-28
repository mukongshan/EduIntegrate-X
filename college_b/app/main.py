from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .integration import MockIntegrationGateway
from .repository import CourseFullError, InMemoryCollegeBRepository, NotFoundError, ValidationError
from .xml_utils import get_text, parse_xml, xml_response


def _parse_choice(root):
    choices = root.find("choices")
    choice = choices.find("choice") if choices is not None else root.find("choice")
    if choice is None:
        choice = root
    student_id = get_text(choice, "sid") or get_text(root, "sid")
    course_id = get_text(choice, "cid") or get_text(root, "cid")
    score_text = get_text(choice, "score", "0") or "0"
    if not student_id or not course_id:
        raise ValueError("missing sid or cid")
    try:
        score = int(score_text)
    except ValueError as exc:
        raise ValueError("invalid score") from exc
    return student_id, course_id, score


def _parse_login(root):
    username = get_text(root, "username") or get_text(root, "account") or get_text(root, "acc")
    password = get_text(root, "password") or get_text(root, "passwd")
    if not username or not password:
        raise ValueError("missing username or password")
    return username, password


def _parse_withdraw(root, path_enrollment_id: str):
    enrollment_id = get_text(root, "enrollmentId") or path_enrollment_id
    if not enrollment_id:
        raise ValueError("missing enrollmentId")
    student_id = get_text(root, "studentId") or get_text(root, "sid")
    course_id = get_text(root, "courseId") or get_text(root, "cid")
    return enrollment_id, student_id, course_id


def create_app(repository=None, gateway=None) -> FastAPI:
    settings = Settings()
    if repository is None:
        if settings.storage_backend.lower() == "oracle":
            from .oracle_repository import OracleCollegeBRepository

            if not settings.oracle_dsn.strip():
                raise ValueError("missing ORACLE_DSN in .env")
            repository = OracleCollegeBRepository(
                dsn=settings.oracle_dsn,
                user=settings.oracle_user,
                password=settings.oracle_password,
                college_id=settings.college_id,
                init_schema=True,
                reset_data=False,
            )
        else:
            repository = InMemoryCollegeBRepository(college_id=settings.college_id)
    if gateway is None:
        gateway = MockIntegrationGateway(repository)

    app = FastAPI(title="College B Backend", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.settings = settings
    app.state.repository = repository
    app.state.gateway = gateway

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/api/v1/auth/login")
    async def login(request: Request):
        try:
            root = parse_xml(await request.body())
            username, password = _parse_login(root)
        except Exception as exc:
            return xml_response(400, str(exc), status_code=400)
        account = repository.get_account(username)
        if account is None or account.password != password:
            return xml_response(401, "invalid credentials", status_code=401)
        student = repository.get_student_by_account(username)
        data = {
            "user": {
                "username": account.username,
                "role": account.role,
                "studentId": student.student_id if student else "",
            }
        }
        return xml_response(0, "success", data=data)

    @app.get("/api/v1/courses")
    async def list_courses():
        data = {
            "meta": {"collegeId": settings.college_id},
            "courses": repository.courses_to_dicts(repository.list_courses()),
        }
        return xml_response(0, "success", data=data)

    @app.get("/api/v1/students/{student_id}")
    async def get_student(student_id: str):
        student = repository.get_student(student_id)
        if student is None:
            return xml_response(404, "student not found", {"studentId": student_id}, 404)
        data = {"student": {"id": student.student_id, "name": student.name, "major": student.major, "gender": student.gender}}
        return xml_response(0, "success", data=data)

    @app.get("/internal/v1/stats/summary")
    async def stats_summary():
        return xml_response(0, "success", {"summary": repository.get_stats_summary()})

    @app.get("/api/v1/shared-courses")
    async def shared_courses(collegeId: str = settings.college_id):
        data = {
            "meta": {"collegeId": collegeId},
            "classes": gateway.list_shared_courses(collegeId),
        }
        return xml_response(0, "success", data=data)

    @app.post("/api/v1/enrollments")
    async def create_enrollment(request: Request):
        try:
            root = parse_xml(await request.body())
            home_college_id = get_text(root, "meta/homeCollegeId") or settings.college_id
            target_college_id = get_text(root, "meta/targetCollegeId") or settings.college_id
            student_id, course_id, score = _parse_choice(root)
        except Exception as exc:
            return xml_response(400, str(exc), status_code=400)
        if home_college_id != settings.college_id:
            return xml_response(400, "home college mismatch", status_code=400)
        try:
            if target_college_id.upper() == settings.college_id.upper():
                record, created = repository.create_local_enrollment(student_id, course_id, score)
                message = "enrollment created" if created else "duplicate enrollment"
                data = {"enrollmentId": record.enrollment_id, "status": record.status, "targetCollegeId": target_college_id}
                return xml_response(0, message, data=data)
            result = gateway.submit_enrollment(
                home_college_id=home_college_id,
                target_college_id=target_college_id,
                student_id=student_id,
                course_id=course_id,
                score=score,
            )
            return xml_response(0, "enrollment accepted", data=result)
        except NotFoundError as exc:
            return xml_response(404, str(exc), status_code=404)
        except CourseFullError as exc:
            return xml_response(400, str(exc), status_code=400)
        except ValidationError as exc:
            return xml_response(400, str(exc), status_code=400)

    @app.post("/api/v1/enrollments/{enrollment_id}/withdraw")
    async def withdraw_enrollment(enrollment_id: str, request: Request):
        try:
            body = await request.body()
            if body.strip():
                root = parse_xml(body)
                req_enrollment_id, student_id, course_id = _parse_withdraw(root, enrollment_id)
            else:
                req_enrollment_id, student_id, course_id = enrollment_id, None, None
        except Exception as exc:
            return xml_response(400, str(exc), status_code=400)
        try:
            if repository.get_enrollment(req_enrollment_id) is not None:
                record, _ = repository.withdraw_enrollment(
                    enrollment_id=req_enrollment_id,
                    student_id=student_id,
                    course_id=course_id,
                )
                return xml_response(0, "withdraw success", data={"enrollmentId": record.enrollment_id, "status": record.status})
            result = gateway.withdraw_enrollment(req_enrollment_id)
            return xml_response(0, "withdraw accepted", data=result)
        except NotFoundError as exc:
            return xml_response(404, str(exc), status_code=404)

    @app.post("/internal/v1/enrollments/writeback")
    async def writeback(request: Request):
        try:
            root = parse_xml(await request.body())
            source_college_id = get_text(root, "meta/sourceCollegeId") or ""
            target_college_id = get_text(root, "meta/targetCollegeId") or ""
            status = get_text(root, "meta/status", "ENROLLED") or "ENROLLED"
            student_id, course_id, score = _parse_choice(root)
        except Exception as exc:
            return xml_response(400, str(exc), status_code=400)
        try:
            record, created = repository.apply_inbound_writeback(
                source_college_id=source_college_id,
                target_college_id=target_college_id,
                student_id=student_id,
                course_id=course_id,
                score=score,
                status=status,
            )
            message = "writeback success" if created else "duplicate enrollment"
            return xml_response(
                0,
                message,
                data={"enrollmentId": record.enrollment_id, "collegeId": target_college_id, "status": record.status},
            )
        except NotFoundError as exc:
            return xml_response(404, str(exc), status_code=404)
        except CourseFullError as exc:
            return xml_response(400, str(exc), status_code=400)
        except ValidationError as exc:
            return xml_response(400, str(exc), status_code=400)

    @app.post("/internal/v1/enrollments/withdraw")
    async def withdraw_writeback(request: Request):
        try:
            root = parse_xml(await request.body())
            enrollment_id = get_text(root, "enrollmentId")
            student_id = get_text(root, "studentId")
            course_id = get_text(root, "courseId")
            if not enrollment_id:
                raise ValueError("missing enrollmentId")
        except Exception as exc:
            return xml_response(400, str(exc), status_code=400)
        try:
            record, _ = repository.withdraw_enrollment(
                enrollment_id=enrollment_id,
                student_id=student_id,
                course_id=course_id,
            )
            return xml_response(0, "withdraw writeback success", data={"enrollmentId": record.enrollment_id, "status": record.status})
        except NotFoundError as exc:
            return xml_response(404, str(exc), status_code=404)

    return app

app = None
