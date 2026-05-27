"""集成服务器与学院系统的交互网关"""
import logging
from pathlib import Path
from typing import Optional

import httpx
import xmltodict

from .config import Settings
from .models import EnrollmentRecord, EnrollmentStatus
from .xml_utils import parse_xml, transform_xml_with_xslt

logger = logging.getLogger(__name__)


class CollegeGateway:
    """与学院系统交互的网关"""
    
    def __init__(self, settings: Settings):
        """初始化网关"""
        self.settings = settings
        self.college_urls = {
            "A": settings.college_a_url,
            "B": settings.college_b_url,
            "C": settings.college_c_url,
        }
        self.timeout = 10
        self.xsd_dir = Path(__file__).parent / "xsd"
        self.xsl_dir = Path(__file__).parent / "xsl"
    
    def get_college_url(self, college_id: str) -> Optional[str]:
        """获取学院服务 URL"""
        return self.college_urls.get(college_id.upper())

    async def list_shared_courses(self, college_id: str | None = None) -> list[dict]:
        """从各学院服务汇总共享课程。

        学院端当前提供 `/api/v1/courses`，返回统一课程字段并带 `share` 标记。
        集成服务器只输出统一 XML Schema 中定义的课程字段。
        """
        target_college = college_id.upper() if college_id else None
        college_items = self.college_urls.items()
        if target_college:
            college_items = [(target_college, self.college_urls.get(target_college))]

        courses: list[dict] = []
        for source_college_id, college_url in college_items:
            if not college_url:
                continue
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{college_url}/api/v1/courses",
                        headers={"Accept": "application/xml"},
                        timeout=self.timeout,
                    )
                if response.status_code != 200:
                    logger.warning("[SharedCourses] %s returned HTTP %s", source_college_id, response.status_code)
                    continue
                parsed = parse_xml(response.text)
                data = parsed.get("Response", {}).get("data", {})
                raw_courses = data.get("courses", {}).get("course", [])
                if isinstance(raw_courses, dict):
                    raw_courses = [raw_courses]
                for course in raw_courses:
                    if str(course.get("share", "")).upper() != "Y":
                        continue
                    courses.append({
                        "id": course.get("id", ""),
                        "name": course.get("name", ""),
                        "time": course.get("time", "0"),
                        "score": course.get("score", "0"),
                        "teacher": course.get("teacher", ""),
                        "location": course.get("location", ""),
                    })
            except Exception as exc:
                logger.warning("[SharedCourses] Failed to fetch %s courses: %s", source_college_id, exc)
        return courses

    async def get_live_college_summary(self) -> dict:
        """优先从学院端实时拉取课程统计，返回按学院聚合的统计数据。"""
        summary = {}
        for college_id, college_url in self.college_urls.items():
            if not college_url:
                continue
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{college_url}/api/v1/courses",
                        headers={"Accept": "application/xml"},
                        timeout=self.timeout,
                    )
                if response.status_code != 200:
                    continue
                parsed = parse_xml(response.text)
                raw_courses = parsed.get("Response", {}).get("data", {}).get("courses", {}).get("course", [])
                if isinstance(raw_courses, dict):
                    raw_courses = [raw_courses]
                summary[college_id] = {
                    "course_count": len(raw_courses),
                    "shared_course_count": sum(1 for c in raw_courses if str(c.get("share", "")).upper() == "Y"),
                }
            except Exception as exc:
                logger.warning("[Stats] Failed to fetch %s live summary: %s", college_id, exc)
        return summary
    
    async def writeback_enrollment(self, enrollment: EnrollmentRecord) -> tuple[bool, Optional[str], Optional[str]]:
        """
        向学院写回选课记录
        
        返回：(success, error_message, response_xml)
        """
        college_url = self.get_college_url(enrollment.target_college_id)
        if not college_url:
            error = f"Unknown college: {enrollment.target_college_id}"
            logger.error(f"[Writeback] {error}")
            return False, error, None
        
        # 构建写回请求 XML
        writeback_xml = self._build_writeback_request(enrollment)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{college_url}/internal/v1/enrollments/writeback",
                    content=writeback_xml,
                    headers={
                        "Content-Type": "application/xml",
                        "Accept": "application/xml",
                        "Authorization": f"Bearer {self.settings.api_key}",
                    },
                    timeout=self.timeout,
                )
                
                response_xml = response.text
                
                # 检查响应状态码
                if response.status_code == 200:
                    # 尝试解析响应，检查业务 code
                    try:
                        resp_data = parse_xml(response_xml)
                        code = int(resp_data.get("Response", {}).get("code", "-1"))
                        if code == 0:
                            logger.info(f"[Writeback] Successfully wrote back enrollment {enrollment.enrollment_id}")
                            return True, None, response_xml
                        else:
                            error = resp_data.get("Response", {}).get("message", "Unknown error")
                            logger.error(f"[Writeback] College returned error: {error}")
                            return False, error, response_xml
                    except Exception as e:
                        logger.error(f"[Writeback] Failed to parse response: {str(e)}")
                        return False, f"Failed to parse response: {str(e)}", response_xml
                else:
                    error = f"HTTP {response.status_code}: {response_xml[:200]}"
                    logger.error(f"[Writeback] HTTP error: {error}")
                    return False, error, response_xml
        
        except httpx.TimeoutException:
            error = "Request timeout"
            logger.error(f"[Writeback] Timeout for {college_url}")
            return False, error, None
        except httpx.ConnectError as e:
            error = f"Connection failed: {str(e)}"
            logger.error(f"[Writeback] Connection error: {error}")
            return False, error, None
        except Exception as e:
            error = f"Unexpected error: {str(e)}"
            logger.error(f"[Writeback] Unexpected error: {error}")
            return False, error, None
    
    async def withdraw_enrollment(self, enrollment: EnrollmentRecord) -> tuple[bool, Optional[str], Optional[str]]:
        """
        向学院写回退选记录
        
        返回：(success, error_message, response_xml)
        """
        college_url = self.get_college_url(enrollment.target_college_id)
        if not college_url:
            error = f"Unknown college: {enrollment.target_college_id}"
            logger.error(f"[Withdraw] {error}")
            return False, error, None
        
        # 构建退选请求 XML
        withdraw_xml = self._build_withdraw_request(enrollment)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{college_url}/internal/v1/enrollments/withdraw",
                    content=withdraw_xml,
                    headers={
                        "Content-Type": "application/xml",
                        "Accept": "application/xml",
                        "Authorization": f"Bearer {self.settings.api_key}",
                    },
                    timeout=self.timeout,
                )
                
                response_xml = response.text
                
                if response.status_code == 200:
                    try:
                        resp_data = parse_xml(response_xml)
                        code = int(resp_data.get("Response", {}).get("code", "-1"))
                        if code == 0:
                            logger.info(f"[Withdraw] Successfully withdrew enrollment {enrollment.enrollment_id}")
                            return True, None, response_xml
                        else:
                            error = resp_data.get("Response", {}).get("message", "Unknown error")
                            logger.error(f"[Withdraw] College returned error: {error}")
                            return False, error, response_xml
                    except Exception as e:
                        logger.error(f"[Withdraw] Failed to parse response: {str(e)}")
                        return False, f"Failed to parse response: {str(e)}", response_xml
                else:
                    error = f"HTTP {response.status_code}: {response_xml[:200]}"
                    logger.error(f"[Withdraw] HTTP error: {error}")
                    return False, error, response_xml
        
        except httpx.TimeoutException:
            error = "Request timeout"
            logger.error(f"[Withdraw] Timeout for {college_url}")
            return False, error, None
        except Exception as e:
            error = f"Unexpected error: {str(e)}"
            logger.error(f"[Withdraw] Unexpected error: {error}")
            return False, error, None
    
    def _build_writeback_request(self, enrollment: EnrollmentRecord) -> str:
        """构建写回请求 XML"""
        from datetime import datetime
        
        data = {
            "WritebackRequest": {
                "meta": {
                    "sourceCollegeId": enrollment.home_college_id,
                    "targetCollegeId": enrollment.target_college_id,
                    "status": EnrollmentStatus.ENROLLED.value,
                    "enrollmentId": enrollment.enrollment_id,
                    "requestTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
                "choices": {
                    "choice": {
                        "sid": enrollment.student_id,
                        "cid": enrollment.course_id,
                        "score": str(enrollment.score),
                    }
                }
            }
        }
        unified_xml = xmltodict.unparse(data, pretty=True)
        xsl_path = self.xsl_dir / f"writeback_to_{enrollment.target_college_id.upper()}.xsl"
        if xsl_path.exists():
            return transform_xml_with_xslt(unified_xml, xsl_path)
        return unified_xml
    
    def _build_withdraw_request(self, enrollment: EnrollmentRecord) -> str:
        """构建退选请求 XML"""
        target_enrollment_id = enrollment.target_enrollment_id or enrollment.enrollment_id
        data = {
            "WithdrawWritebackRequest": {
                "enrollmentId": target_enrollment_id,
                "studentId": enrollment.student_id,
                "courseId": enrollment.course_id,
                "status": EnrollmentStatus.WITHDRAWN.value,
            }
        }
        unified_xml = xmltodict.unparse(data, pretty=True)
        xsl_path = self.xsl_dir / f"withdraw_to_{enrollment.target_college_id.upper()}.xsl"
        if xsl_path.exists():
            return transform_xml_with_xslt(unified_xml, xsl_path)
        return unified_xml
