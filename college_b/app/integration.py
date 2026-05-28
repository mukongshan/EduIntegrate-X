from __future__ import annotations

from .repository import InMemoryCollegeBRepository


class MockIntegrationGateway:
    def __init__(self, repository: InMemoryCollegeBRepository) -> None:
        self.repository = repository
        self.shared_catalog = {
            "B": [
                {"id": "A001", "name": "数据库系统", "time": 0, "score": 3, "teacher": "张老师", "location": "1-301"},
                {"id": "C001", "name": "软件工程实践", "time": 32, "score": 3, "teacher": "陈老师", "location": "C-401"},
                {"id": "C002", "name": "Web开发", "time": 24, "score": 2, "teacher": "刘老师", "location": "C-302"},
            ]
        }

    def list_shared_courses(self, college_id: str) -> list[dict]:
        return self.shared_catalog.get(college_id.upper(), self.shared_catalog["B"])

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
        return {
            "enrollmentId": request["enrollmentId"],
            "status": request["status"],
        }
