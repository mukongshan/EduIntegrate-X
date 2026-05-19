from __future__ import annotations

import os
import xml.etree.ElementTree as ET

import pyodbc
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from college_a.app.integration import MockIntegrationGateway
from college_a.app.main import create_app
from college_a.app.sqlserver_repository import SqlServerCollegeARepository


load_dotenv()


pytestmark = pytest.mark.skipif(os.getenv("RUN_SQLSERVER_TESTS") != "1", reason="real SQL Server test disabled")


TEST_DATABASE = os.getenv("COLLEGE_A_TEST_DATABASE") or os.getenv("MSSQL_DATABASE", "")
TEST_SERVER = os.getenv("MSSQL_SERVER") or (
    f"{os.getenv('MSSQL_HOST')},{os.getenv('MSSQL_PORT', '1433')}" if os.getenv("MSSQL_HOST") else ""
)
TEST_DRIVER = os.getenv("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server")
TEST_TRUSTED = os.getenv("MSSQL_TRUSTED_CONNECTION", "true").strip().lower() in {"1", "true", "yes", "y", "on"}
TEST_USER = os.getenv("MSSQL_USER", "")
TEST_PASSWORD = os.getenv("MSSQL_PASSWORD", "")


def _xml_text(response_text: str, path: str) -> str | None:
    root = ET.fromstring(response_text)
    node = root.find(path)
    return None if node is None or node.text is None else node.text


def _connect(database: str):
    if TEST_TRUSTED:
        conn_str = (
            f"DRIVER={{{TEST_DRIVER}}};SERVER={TEST_SERVER};DATABASE={database};"
            "Trusted_Connection=yes;TrustServerCertificate=yes;Encrypt=no;"
        )
    else:
        conn_str = (
            f"DRIVER={{{TEST_DRIVER}}};SERVER={TEST_SERVER};DATABASE={database};"
            f"UID={TEST_USER};PWD={TEST_PASSWORD};TrustServerCertificate=yes;Encrypt=no;"
        )
    return pyodbc.connect(conn_str, autocommit=False)


@pytest.fixture(scope="module")
def sql_repo():
    if not TEST_SERVER or not TEST_DATABASE:
        pytest.skip("missing SQL Server env config")
    repo = SqlServerCollegeARepository(
        server=TEST_SERVER,
        database=TEST_DATABASE,
        driver=TEST_DRIVER,
        trusted_connection=TEST_TRUSTED,
        user=TEST_USER,
        password=TEST_PASSWORD,
        college_id="A",
        init_schema=True,
        reset_data=True,
    )
    return repo


@pytest.fixture()
def client(sql_repo):
    app = create_app(repository=sql_repo, gateway=MockIntegrationGateway(sql_repo))
    return TestClient(app)


def test_real_sqlserver_writeback_and_withdraw(client, sql_repo):
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

    conn = _connect(TEST_DATABASE)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(1) FROM [dbo].[Enrollment] WHERE [课程编号] = ? AND [学生编号] = ?", "A001", "S2024001")
        assert cursor.fetchone()[0] == 1
        cursor.execute("SELECT [status] FROM [dbo].[EnrollmentLog] WHERE [enrollment_id] = ?", enrollment_id)
        assert cursor.fetchone()[0] == "ENROLLED"
    finally:
        conn.close()

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

    conn = _connect(TEST_DATABASE)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(1) FROM [dbo].[Enrollment] WHERE [课程编号] = ? AND [学生编号] = ?", "A001", "S2024001")
        assert cursor.fetchone()[0] == 0
        cursor.execute("SELECT [status] FROM [dbo].[EnrollmentLog] WHERE [enrollment_id] = ?", enrollment_id)
        assert cursor.fetchone()[0] == "WITHDRAWN"
    finally:
        conn.close()
