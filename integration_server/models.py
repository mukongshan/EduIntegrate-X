"""集成服务器数据模型"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class EnrollmentStatus(str, Enum):
    """选课状态枚举"""
    PENDING_WRITEBACK = "PENDING_WRITEBACK"
    ENROLLED = "ENROLLED"
    WRITEBACK_FAILED = "WRITEBACK_FAILED"
    WITHDRAW_PENDING = "WITHDRAW_PENDING"
    WITHDRAWN = "WITHDRAWN"


class RetryStatus(str, Enum):
    """重试状态"""
    NOT_RETRIED = "NOT_RETRIED"
    RETRYING = "RETRYING"
    RETRY_SUCCESS = "RETRY_SUCCESS"
    RETRY_FAILED = "RETRY_FAILED"


@dataclass
class EnrollmentRecord:
    """选课记录（集成服务器内部记录）"""
    enrollment_id: str
    home_college_id: str
    target_college_id: str
    student_id: str
    course_id: str
    score: int = 0
    status: EnrollmentStatus = EnrollmentStatus.PENDING_WRITEBACK
    retry_status: RetryStatus = RetryStatus.NOT_RETRIED
    retry_count: int = 0
    raw_request_xml: str = ""
    raw_response_xml: str = ""
    target_enrollment_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    writeback_attempted_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转字典"""
        return {
            "enrollment_id": self.enrollment_id,
            "home_college_id": self.home_college_id,
            "target_college_id": self.target_college_id,
            "student_id": self.student_id,
            "course_id": self.course_id,
            "score": self.score,
            "status": self.status.value,
            "retry_status": self.retry_status.value,
            "retry_count": self.retry_count,
            "target_enrollment_id": self.target_enrollment_id or "",
            "error_message": self.error_message or "",
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class SharedCourse:
    """共享课程（来自学院导出）"""
    id: str
    name: str
    time: int = 0
    score: int = 0
    teacher: str = ""
    location: str = ""
    college_id: str = ""
    
    def to_dict(self) -> dict:
        """转字典"""
        return {
            "id": self.id,
            "name": self.name,
            "time": self.time,
            "score": self.score,
            "teacher": self.teacher,
            "location": self.location,
            "collegeId": self.college_id,
        }
