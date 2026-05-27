from __future__ import annotations

import os
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient

from college_c.app.integration import MockIntegrationGateway
from college_c.app.main import create_app
from college_c.app.mysql_repository import MySqlCollegeCRepository, pymysql


pytestmark = pytest.mark.skipif(os.getenv("RUN_MYSQL_TESTS") != "1", reason="real MySQL test disabled")


def _xml_text(response_text: str, path: str) -> str | None:
    root = ET.fromstring(response_text)
    node = root.find(path)
    return None if node is None or node.text is None else node.text


def test_real_mysql_writeback_and_withdraw():
    if pymysql is None:
        pytest.skip("pymysql is not installed")
    database = os.getenv("COLLEGE_C_TEST_DATABASE") or os.getenv("MYSQL_DATABASE", "")
    user = os.getenv("MYSQL_USER", "")
    if not database or not user:
        pytest.skip("missing MySQL env config")
    repository = MySqlCollegeCRepository(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=database,
        user=user,
        password=os.getenv("MYSQL_PASSWORD", ""),
        charset=os.getenv("MYSQL_CHARSET", "utf8mb4"),
        college_id="C",
        init_schema=True,
        reset_data=True,
    )
    app = create_app(repository=repository, gateway=MockIntegrationGateway(repository))
    client = TestClient(app)
    payload = """
    <WritebackRequest>
      <meta>
        <sourceCollegeId>A</sourceCollegeId>
        <targetCollegeId>C</targetCollegeId>
        <status>ENROLLED</status>
      </meta>
      <choices>
        <choice>
          <sid>C2024001</sid>
          <cid>C001</cid>
          <score>88</score>
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
    enrollment_id = _xml_text(response.text, "data/enrollmentId")
    assert enrollment_id
    assert repository.get_enrollment(enrollment_id).status == "ENROLLED"

    withdraw_response = client.post(f"/api/v1/enrollments/{enrollment_id}/withdraw")
    assert withdraw_response.status_code == 200
    assert _xml_text(withdraw_response.text, "data/status") == "WITHDRAWN"
    assert repository.get_enrollment(enrollment_id).status == "WITHDRAWN"
