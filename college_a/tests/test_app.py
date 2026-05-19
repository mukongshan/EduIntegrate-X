from __future__ import annotations

import xml.etree.ElementTree as ET

from fastapi.testclient import TestClient

from college_a.app.integration import MockIntegrationGateway
from college_a.app.main import create_app
from college_a.app.repository import InMemoryCollegeARepository


def _xml_text(response_text: str, path: str) -> str | None:
    root = ET.fromstring(response_text)
    node = root.find(path)
    return None if node is None or node.text is None else node.text


def _client():
    repository = InMemoryCollegeARepository(college_id="A")
    app = create_app(repository=repository, gateway=MockIntegrationGateway(repository))
    return TestClient(app), app


def test_health():
    client, _ = _client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_success():
    client, _ = _client()
    response = client.post(
        "/api/v1/auth/login",
        content="""
        <LoginRequest>
          <username>a_student1</username>
          <password>123456</password>
        </LoginRequest>
        """,
        headers={"Content-Type": "application/xml", "Accept": "application/xml"},
    )
    assert response.status_code == 200
    assert _xml_text(response.text, "code") == "0"
    assert _xml_text(response.text, "data/user/username") == "a_student1"
    assert _xml_text(response.text, "data/user/studentId") == "S2024001"


def test_shared_courses():
    client, _ = _client()
    response = client.get("/api/v1/shared-courses?collegeId=A")
    assert response.status_code == 200
    assert _xml_text(response.text, "code") == "0"
    assert _xml_text(response.text, "data/meta/collegeId") == "A"
    assert _xml_text(response.text, "data/classes/class/id") is not None


def test_inbound_writeback_and_withdraw():
    client, app = _client()
    payload = """
    <WritebackRequest>
      <meta>
        <sourceCollegeId>C</sourceCollegeId>
        <targetCollegeId>A</targetCollegeId>
        <status>ENROLLED</status>
      </meta>
      <choices>
        <choice>
          <sid>S2024001</sid>
          <cid>A001</cid>
          <score>95</score>
        </choice>
      </choices>
    </WritebackRequest>
    """
    response = client.post(
        "/internal/v1/enrollments/writeback",
        content=payload,
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
      <studentId>S2024001</studentId>
      <courseId>A001</courseId>
    </WithdrawWritebackRequest>
    """
    withdraw_response = client.post(
        "/internal/v1/enrollments/withdraw",
        content=withdraw_payload,
        headers={"Content-Type": "application/xml", "Accept": "application/xml"},
    )
    assert withdraw_response.status_code == 200
    assert _xml_text(withdraw_response.text, "data/status") == "WITHDRAWN"


def test_outbound_enrollment_mock():
    client, app = _client()
    payload = """
    <EnrollmentRequest>
      <meta>
        <homeCollegeId>A</homeCollegeId>
        <targetCollegeId>B</targetCollegeId>
        <requestTime>2026-05-17 10:30:00</requestTime>
      </meta>
      <choices>
        <choice>
          <sid>S2024001</sid>
          <cid>B001</cid>
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
    enrollment_id = _xml_text(response.text, "data/enrollmentId")
    assert app.state.repository.get_outbound_request(enrollment_id) is not None
