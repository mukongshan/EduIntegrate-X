from __future__ import annotations

from .repository import InMemoryCollegeCRepository, NotFoundError


class MockIntegrationGateway:
    def __init__(self, repository: InMemoryCollegeCRepository) -> None:
        self.repository = repository
        self.shared_catalog = {
            "C": [
                {"id": "A001", "name": "数据库系统", "time": 0, "score": 3, "teacher": "张老师", "location": "1-301"},
                {"id": "A003", "name": "数仓基础", "time": 0, "score": 2, "teacher": "王老师", "location": "3-105"},
                {"id": "B001", "name": "分布式系统", "time": 32, "score": 3, "teacher": "周老师", "location": "B-201"},
            ]
        }

    def list_shared_courses(self, college_id: str) -> list[dict]:
        return self.shared_catalog.get(college_id.upper(), self.shared_catalog["C"])

    def submit_enrollment(self, *, home_college_id: str, target_college_id: str, student_id: str, course_id: str, score: int) -> dict:
        enrollment_id = self.repository.register_outbound_request(
            home_college_id=home_college_id,
            target_college_id=target_college_id,
            student_id=student_id,
            course_id=course_id,
            score=score,
        )
        return {
            "enrollmentId": enrollment_id,
            "status": "PENDING_WRITEBACK",
            "targetCollegeId": target_college_id,
        }

    def withdraw_enrollment(self, enrollment_id: str) -> dict:
        request = self.repository.withdraw_outbound_request(enrollment_id)
        if request is None:
            raise NotFoundError("enrollment not found")
        return {
            "enrollmentId": request["enrollmentId"],
            "status": request["status"],
        }
