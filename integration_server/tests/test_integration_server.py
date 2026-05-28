"""集成服务器测试"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import xmltodict

from integration_server.app import create_app
from integration_server.config import Settings
from integration_server.models import EnrollmentStatus
from integration_server.repository import IntegrationRepository


@pytest.fixture
def temp_db():
    """创建临时数据库"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        yield db_path


@pytest.fixture
def test_settings(temp_db):
    """创建测试配置"""
    settings = Settings(
        db_path=temp_db,
        college_a_url="http://localhost:8000",
        college_b_url="http://localhost:8001",
        college_c_url="http://localhost:8002",
    )
    return settings


@pytest.fixture
def auth_headers(test_settings):
    return {"Authorization": f"Bearer {test_settings.api_key}"}


@pytest.fixture
def client(test_settings):
    """创建测试客户端"""
    app = create_app(test_settings)
    return TestClient(app)


@pytest.fixture
def repo(test_settings):
    """创建仓库实例"""
    return IntegrationRepository(test_settings.db_path)


class TestHealthCheck:
    """健康检查测试"""
    
    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestSharedCourses:
    """共享课程接口测试"""
    
    def test_get_shared_courses_all(self, client):
        """获取所有共享课程"""
        response = client.get("/api/v1/shared-courses")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/xml")
        
        # 解析 XML 响应
        data = xmltodict.parse(response.text)
        assert data["Response"]["code"] == "0"
        assert "classes" in data["Response"]["data"]
        courses = data["Response"]["data"]["classes"]["class"]
        first_course = courses[0] if isinstance(courses, list) else courses
        assert "collegeId" in first_course
    
    def test_get_shared_courses_by_college(self, client):
        """按学院获取共享课程"""
        response = client.get("/api/v1/shared-courses?college_id=A")
        assert response.status_code == 200
        data = xmltodict.parse(response.text)
        assert data["Response"]["code"] == "0"

    def test_get_shared_courses_by_college_camel_param(self, client):
        """按学院获取共享课程（collegeId 参数兼容）"""
        response = client.get("/api/v1/shared-courses?collegeId=A")
        assert response.status_code == 200
        data = xmltodict.parse(response.text)
        assert data["Response"]["code"] == "0"
        assert data["Response"]["data"]["meta"]["collegeId"] == "A"

    def test_get_shared_courses_unknown_college_returns_empty_success(self, client):
        """无匹配课程时也应返回成功与空列表。"""
        response = client.get("/api/v1/shared-courses?collegeId=Z")
        assert response.status_code == 200
        data = xmltodict.parse(response.text)
        assert data["Response"]["code"] == "0"


class TestEnrollment:
    """选课接口测试"""
    
    def test_submit_enrollment_success(self, client, repo):
        """成功提交选课"""
        enrollment_xml = """<?xml version="1.0" encoding="UTF-8"?>
<EnrollmentRequest>
    <meta>
        <homeCollegeId>C</homeCollegeId>
        <targetCollegeId>A</targetCollegeId>
        <requestTime>2026-05-27 10:30:00</requestTime>
    </meta>
    <choices>
        <choice>
            <sid>S2024001</sid>
            <cid>C001</cid>
            <score>0</score>
        </choice>
    </choices>
</EnrollmentRequest>"""
        
        response = client.post(
            "/api/v1/enrollments",
            content=enrollment_xml,
            headers={"Content-Type": "application/xml"}
        )
        
        assert response.status_code == 200
        data = xmltodict.parse(response.text)
        assert data["Response"]["code"] == "0"
        assert "enrollmentId" in data["Response"]["data"]
        
        enrollment_id = data["Response"]["data"]["enrollmentId"]
        # 验证记录已创建
        enrollment = repo.get_enrollment_by_id(enrollment_id)
        assert enrollment is not None
        assert enrollment.student_id == "S2024001"
        assert enrollment.course_id == "C001"
    
    def test_submit_enrollment_duplicate(self, client, repo):
        """重复提交选课（幂等性测试）"""
        enrollment_xml = """<?xml version="1.0" encoding="UTF-8"?>
<EnrollmentRequest>
    <meta>
        <homeCollegeId>C</homeCollegeId>
        <targetCollegeId>A</targetCollegeId>
    </meta>
    <choices>
        <choice>
            <sid>S2024002</sid>
            <cid>C002</cid>
            <score>0</score>
        </choice>
    </choices>
</EnrollmentRequest>"""
        
        # 第一次提交
        response1 = client.post(
            "/api/v1/enrollments",
            content=enrollment_xml,
            headers={"Content-Type": "application/xml"}
        )
        assert response1.status_code == 200
        data1 = xmltodict.parse(response1.text)
        enrollment_id_1 = data1["Response"]["data"]["enrollmentId"]
        
        # 第二次提交（重复）
        response2 = client.post(
            "/api/v1/enrollments",
            content=enrollment_xml,
            headers={"Content-Type": "application/xml"}
        )
        assert response2.status_code == 200
        data2 = xmltodict.parse(response2.text)
        
        # 应该返回 409（重复）或相同的 enrollmentId
        assert data2["Response"]["code"] == "409" or data2["Response"]["data"]["enrollmentId"] == enrollment_id_1
    
    def test_submit_enrollment_invalid_xml(self, client):
        """提交无效 XML"""
        response = client.post(
            "/api/v1/enrollments",
            content="<invalid>xml",
            headers={"Content-Type": "application/xml"}
        )
        
        assert response.status_code == 200
        data = xmltodict.parse(response.text)
        assert data["Response"]["code"] != "0"  # 应该是错误


class TestWithdraw:
    """退选接口测试"""
    
    def test_withdraw_enrollment_not_found(self, client):
        """退选不存在的选课"""
        response = client.post(
            "/api/v1/enrollments/E999999/withdraw",
            headers={"Content-Type": "application/xml"}
        )
        
        assert response.status_code == 200
        data = xmltodict.parse(response.text)
        assert data["Response"]["code"] == "404"
    
    def test_withdraw_enrollment_success(self, client, repo):
        """成功退选"""
        # 先创建选课
        enrollment_xml = """<?xml version="1.0" encoding="UTF-8"?>
<EnrollmentRequest>
    <meta>
        <homeCollegeId>C</homeCollegeId>
        <targetCollegeId>A</targetCollegeId>
    </meta>
    <choices>
        <choice>
            <sid>S2024003</sid>
            <cid>C003</cid>
            <score>0</score>
        </choice>
    </choices>
</EnrollmentRequest>"""
        
        response = client.post(
            "/api/v1/enrollments",
            content=enrollment_xml,
            headers={"Content-Type": "application/xml"}
        )
        data1 = xmltodict.parse(response.text)
        enrollment_id = data1["Response"]["data"]["enrollmentId"]
        
        # 模拟手动将状态改为 ENROLLED（实际应该由写回完成）
        from integration_server.models import EnrollmentStatus
        repo.update_enrollment_status(enrollment_id, EnrollmentStatus.ENROLLED)
        
        # 退选
        response2 = client.post(
            f"/api/v1/enrollments/{enrollment_id}/withdraw",
            headers={"Content-Type": "application/xml"}
        )
        
        assert response2.status_code == 200
        data2 = xmltodict.parse(response2.text)
        assert data2["Response"]["code"] == "0"


class TestStats:
    """统计接口测试"""
    
    def test_get_stats_summary(self, client, auth_headers):
        """获取统计汇总"""
        response = client.get("/api/v1/stats/summary", headers=auth_headers)
        assert response.status_code == 200
        data = xmltodict.parse(response.text)
        assert data["Response"]["code"] == "0"
        assert "Summary" in data["Response"]["data"]
        assert "total" in data["Response"]["data"]["Summary"]

    def test_get_stats_summary_prefers_live_college_stats(self, client, auth_headers):
        """统计汇总优先使用学院端实时 50/10/250 数据。"""
        from integration_server.app import _app_state

        class FakeGateway:
            async def get_live_college_summary(self):
                return {
                    college: {
                        "student_count": 50,
                        "course_count": 10,
                        "total_enrollments": 250,
                        "enrolled_count": 250,
                        "incoming_enrollments": 0,
                        "shared_course_count": 5,
                    }
                    for college in ("A", "B", "C")
                }

        _app_state["gateway"] = FakeGateway()
        response = client.get("/api/v1/stats/summary", headers=auth_headers)
        assert response.status_code == 200
        data = xmltodict.parse(response.text)
        colleges = data["Response"]["data"]["Summary"]["college"]
        assert all(item["studentCount"] == "50" for item in colleges)
        assert all(item["courseCount"] == "10" for item in colleges)
        assert all(item["enrollmentCount"] == "250" for item in colleges)
        assert data["Response"]["data"]["Summary"]["total"]["studentCount"] == "150"
        assert data["Response"]["data"]["Summary"]["total"]["courseCount"] == "30"
        assert data["Response"]["data"]["Summary"]["total"]["enrollmentCount"] == "750"


class TestStudentEnrollments:
    """学生选课列表接口测试"""

    def test_list_student_enrollments_excludes_withdrawn_records(self, client, repo):
        """只返回当前未退选的记录。"""
        from integration_server.models import EnrollmentRecord, EnrollmentStatus

        active = EnrollmentRecord(
            enrollment_id="E_STU_ACTIVE",
            home_college_id="A",
            target_college_id="B",
            student_id="S2024001",
            course_id="B001",
            status=EnrollmentStatus.ENROLLED,
        )
        withdrawn = EnrollmentRecord(
            enrollment_id="E_STU_WITHDRAWN",
            home_college_id="A",
            target_college_id="C",
            student_id="S2024001",
            course_id="C001",
            status=EnrollmentStatus.ENROLLED,
        )
        repo.create_enrollment(active)
        repo.create_enrollment(withdrawn)
        repo.update_enrollment_status("E_STU_WITHDRAWN", EnrollmentStatus.WITHDRAWN)

        response = client.get("/api/v1/students/S2024001/enrollments")
        assert response.status_code == 200
        data = xmltodict.parse(response.text)
        assert data["Response"]["code"] == "0"
        records = data["Response"]["data"]["enrollments"]["enrollment"]
        records = records if isinstance(records, list) else [records]
        ids = {item["enrollmentId"] for item in records}
        assert "E_STU_ACTIVE" in ids
        assert "E_STU_WITHDRAWN" not in ids
        assert records[0]["sid"] == "S2024001"


class TestRepository:
    """仓库测试"""
    
    def test_create_and_get_enrollment(self, repo):
        """创建和获取选课记录"""
        from integration_server.models import EnrollmentRecord
        
        enrollment = EnrollmentRecord(
            enrollment_id="E001",
            home_college_id="C",
            target_college_id="A",
            student_id="S001",
            course_id="C001",
            score=0,
        )
        
        created_id = repo.create_enrollment(enrollment)
        assert created_id == "E001"
        
        retrieved = repo.get_enrollment_by_id("E001")
        assert retrieved is not None
        assert retrieved.student_id == "S001"
        assert retrieved.course_id == "C001"
    
    def test_update_enrollment_status(self, repo):
        """更新选课状态"""
        from integration_server.models import EnrollmentRecord, EnrollmentStatus
        
        enrollment = EnrollmentRecord(
            enrollment_id="E002",
            home_college_id="C",
            target_college_id="A",
            student_id="S002",
            course_id="C002",
        )
        
        repo.create_enrollment(enrollment)
        repo.update_enrollment_status("E002", EnrollmentStatus.ENROLLED)
        
        retrieved = repo.get_enrollment_by_id("E002")
        assert retrieved.status == EnrollmentStatus.ENROLLED
    
    def test_get_stats(self, repo):
        """获取统计信息"""
        from integration_server.models import EnrollmentRecord, EnrollmentStatus
        
        # 创建多条记录
        for i in range(3):
            enrollment = EnrollmentRecord(
                enrollment_id=f"E{i:03d}",
                home_college_id="C",
                target_college_id="A",
                student_id=f"S{i:03d}",
                course_id=f"C{i:03d}",
            )
            repo.create_enrollment(enrollment)
            repo.update_enrollment_status(f"E{i:03d}", EnrollmentStatus.ENROLLED)
        
        stats = repo.get_stats()
        assert "A" in stats
        assert stats["A"]["enrolled_count"] >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
