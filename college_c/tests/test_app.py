from __future__ import annotations

import xml.etree.ElementTree as ET

from fastapi.testclient import TestClient

from college_c.app.integration import MockIntegrationGateway
from college_c.app.main import create_app
from college_c.app.repository import InMemoryCollegeCRepository


def _xml_text(response_text: str, path: str) -> str | None:
    root = ET.fromstring(response_text)
    node = root.find(path)
    return None if node is None or node.text is None else node.text


def _client():
    repository = InMemoryCollegeCRepository(college_id="C")
    app = create_app(repository=repository, gateway=MockIntegrationGateway(repository))
    return TestClient(app), app


def test_health():
    client, _ = _client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_success_with_college_c_account_shape():
    client, _ = _client()
    response = client.post(
        "/api/v1/auth/login",
        content="""
        <LoginRequest>
          <acc>c_student1</acc>
          <passwd>123456</passwd>
        </LoginRequest>
        """,
        headers={"Content-Type": "application/xml", "Accept": "application/xml"},
    )
    assert response.status_code == 200
    assert _xml_text(response.text, "code") == "0"
    assert _xml_text(response.text, "data/user/username") == "c_student1"
    assert _xml_text(response.text, "data/user/studentId") == "C2024001"


def test_list_local_courses_uses_unified_xml_fields():
    client, _ = _client()
    response = client.get("/api/v1/courses")
    assert response.status_code == 200
    assert _xml_text(response.text, "code") == "0"
    assert _xml_text(response.text, "data/meta/collegeId") == "C"
    assert _xml_text(response.text, "data/courses/course/id") == "C001"
    assert _xml_text(response.text, "data/courses/course/time") == "32"


def test_shared_courses_from_mock_integration_server():
    client, _ = _client()
    response = client.get("/api/v1/shared-courses?collegeId=C")
    assert response.status_code == 200
    assert _xml_text(response.text, "code") == "0"
    assert _xml_text(response.text, "data/meta/collegeId") == "C"
    assert _xml_text(response.text, "data/classes/class/id") in {"A001", "A003", "B001"}


def test_local_enrollment_is_idempotent_and_withdrawable():
    client, app = _client()
    payload = """
    <EnrollmentRequest>
      <meta>
        <homeCollegeId>C</homeCollegeId>
        <targetCollegeId>C</targetCollegeId>
        <requestTime>2026-05-21 18:30:00</requestTime>
      </meta>
      <choices>
        <choice>
          <sid>C2024001</sid>
          <cid>C001</cid>
          <score>0</score>
        </choice>
      </choices>
    </EnrollmentRequest>
    """
    response = client.post(
        "/api/v1/enrollments",
        content=payload,
        headers={"Content-Type": "application/xml", "Accept": "application/xml"},
    )
    assert response.status_code == 200
    assert _xml_text(response.text, "message") == "enrollment created"
    enrollment_id = _xml_text(response.text, "data/enrollmentId")
    assert enrollment_id
    assert app.state.repository.get_enrollment(enrollment_id) is not None

    duplicate_response = client.post(
        "/api/v1/enrollments",
        content=payload,
        headers={"Content-Type": "application/xml", "Accept": "application/xml"},
    )
    assert duplicate_response.status_code == 200
    assert _xml_text(duplicate_response.text, "message") == "duplicate enrollment"
    assert _xml_text(duplicate_response.text, "data/enrollmentId") == enrollment_id

    withdraw_response = client.post(f"/api/v1/enrollments/{enrollment_id}/withdraw")
    assert withdraw_response.status_code == 200
    assert _xml_text(withdraw_response.text, "data/status") == "WITHDRAWN"


def test_inbound_writeback_rejects_unshared_course_and_accepts_shared_course():
    client, app = _client()
    unshared_payload = """
    <WritebackRequest>
      <meta>
        <sourceCollegeId>A</sourceCollegeId>
        <targetCollegeId>C</targetCollegeId>
        <status>ENROLLED</status>
      </meta>
      <choices>
        <choice>
          <sid>C2024001</sid>
          <cid>C002</cid>
          <score>91</score>
        </choice>
      </choices>
    </WritebackRequest>
    """
    rejected = client.post(
        "/internal/v1/enrollments/writeback",
        content=unshared_payload,
        headers={"Content-Type": "application/xml", "Accept": "application/xml"},
    )
    assert rejected.status_code == 400
    assert _xml_text(rejected.text, "message") == "course is not shared"

    shared_payload = unshared_payload.replace("<cid>C002</cid>", "<cid>C001</cid>")
    response = client.post(
        "/internal/v1/enrollments/writeback",
        content=shared_payload,
        headers={"Content-Type": "application/xml", "Accept": "application/xml"},
    )
    assert response.status_code == 200
    assert _xml_text(response.text, "code") == "0"
    enrollment_id = _xml_text(response.text, "data/enrollmentId")
    assert enrollment_id
    assert app.state.repository.get_enrollment(enrollment_id) is not None

    withdraw_payload = f"""
    <WithdrawWritebackRequest>
      <enrollmentId>{enrollment_id}</enrollmentId>
      <studentId>C2024001</studentId>
      <courseId>C001</courseId>
    </WithdrawWritebackRequest>
    """
    withdraw_response = client.post(
        "/internal/v1/enrollments/withdraw",
        content=withdraw_payload,
        headers={"Content-Type": "application/xml", "Accept": "application/xml"},
    )
    assert withdraw_response.status_code == 200
    assert _xml_text(withdraw_response.text, "data/status") == "WITHDRAWN"


def test_outbound_cross_college_enrollment_mock():
    client, app = _client()
    payload = """
    <EnrollmentRequest>
      <meta>
        <homeCollegeId>C</homeCollegeId>
        <targetCollegeId>A</targetCollegeId>
        <requestTime>2026-05-21 18:30:00</requestTime>
      </meta>
      <choices>
        <choice>
          <sid>C2024001</sid>
          <cid>A001</cid>
          <score>0</score>
        </choice>
      </choices>
    </EnrollmentRequest>
    """
    response = client.post(
        "/api/v1/enrollments",
        content=payload,
        headers={"Content-Type": "application/xml", "Accept": "application/xml"},
    )
    assert response.status_code == 200
    assert _xml_text(response.text, "code") == "0"
    assert _xml_text(response.text, "data/status") == "PENDING_WRITEBACK"
    enrollment_id = _xml_text(response.text, "data/enrollmentId")
    assert app.state.repository.get_outbound_request(enrollment_id) is not None
