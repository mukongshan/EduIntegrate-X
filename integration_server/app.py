"""集成服务器主程序"""
import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .gateway import CollegeGateway
from .models import EnrollmentRecord, EnrollmentStatus, RetryStatus, SharedCourse
from .repository import IntegrationRepository
from .xml_utils import get_text, parse_xml, validate_xml_fragment, xml_response

logger = logging.getLogger(__name__)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# 全局对象
_app_state = {
    "repository": None,
    "gateway": None,
    "background_tasks_running": False,
}


def get_repository(settings: Settings = Depends(get_settings)) -> IntegrationRepository:
    """获取数据仓库"""
    if _app_state["repository"] is None:
        _app_state["repository"] = IntegrationRepository(settings.db_path)
    return _app_state["repository"]


def get_gateway(settings: Settings = Depends(get_settings)) -> CollegeGateway:
    """获取网关"""
    if _app_state["gateway"] is None:
        _app_state["gateway"] = CollegeGateway(settings)
    return _app_state["gateway"]


def create_app(settings: Settings = None) -> FastAPI:
    """创建 FastAPI 应用"""
    if settings is None:
        settings = get_settings()

    _app_state["repository"] = IntegrationRepository(settings.db_path)
    _app_state["gateway"] = CollegeGateway(settings)
    _app_state["background_tasks_running"] = False
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    
    # 添加 CORS 支持
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # ==================== 工具函数 ====================
    
    def _verify_api_key(request: Request, expected_key: str = settings.api_key) -> bool:
        """验证 API Key"""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return False
        # 支持 "Bearer <key>" 或 "<key>" 格式
        if auth_header.startswith("Bearer "):
            return auth_header[7:] == expected_key
        return auth_header == expected_key
    
    def _generate_enrollment_id() -> str:
        """生成选课 ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = str(uuid.uuid4())[:8].upper()
        return f"E{timestamp}{random_suffix}"

    def _extract_response_enrollment_id(response_xml: str | None) -> str | None:
        """提取目标学院写回后返回的实际选课记录 ID。"""
        if not response_xml:
            return None
        try:
            response_data = parse_xml(response_xml)
            return get_text(response_data.get("Response", {}).get("data", {}), "enrollmentId", "") or None
        except Exception:
            return None
    
    async def _attempt_writeback(enrollment_id: str, repo: IntegrationRepository, gateway: CollegeGateway):
        """尝试写回选课（后台任务）"""
        enrollment = repo.get_enrollment_by_id(enrollment_id)
        if not enrollment:
            logger.warning(f"Enrollment {enrollment_id} not found for writeback")
            return
        
        if enrollment.status == EnrollmentStatus.ENROLLED:
            logger.info(f"Enrollment {enrollment_id} already enrolled, skipping writeback")
            return
        
        logger.info(f"Attempting writeback for enrollment {enrollment_id}")
        
        # 尝试写回
        success, error_message, response_xml = await gateway.writeback_enrollment(enrollment)
        
        if success:
            repo.update_enrollment_status(
                enrollment_id,
                EnrollmentStatus.ENROLLED,
                RetryStatus.RETRY_SUCCESS,
                raw_response_xml=response_xml,
                target_enrollment_id=_extract_response_enrollment_id(response_xml),
            )
            logger.info(f"Writeback succeeded for enrollment {enrollment_id}")
        else:
            repo.increment_retry_count(enrollment_id)
            repo.update_enrollment_status(
                enrollment_id,
                EnrollmentStatus.WRITEBACK_FAILED,
                RetryStatus.RETRYING,
                error_message=error_message,
                raw_response_xml=response_xml,
            )
            logger.error(f"Writeback failed for enrollment {enrollment_id}: {error_message}")
    
    async def _background_retry_task(repo: IntegrationRepository, gateway: CollegeGateway, interval: int = 30):
        """后台重试任务"""
        await asyncio.sleep(5)  # 启动延迟
        while _app_state["background_tasks_running"]:
            try:
                logger.debug("Background retry task: checking pending writebacks...")
                
                # 获取待重试的记录
                pending = repo.list_pending_writebacks()
                for enrollment in pending:
                    if enrollment.retry_count >= settings.writeback_retry_max_attempts:
                        logger.warning(f"Enrollment {enrollment.enrollment_id} exceeded max retry attempts")
                        repo.update_enrollment_status(
                            enrollment.enrollment_id,
                            EnrollmentStatus.WRITEBACK_FAILED,
                            RetryStatus.RETRY_FAILED,
                            error_message="Max retry attempts exceeded",
                        )
                        continue
                    
                    # 检查是否应该重试（根据上次尝试时间）
                    if enrollment.writeback_attempted_at:
                        time_since_last = datetime.now() - enrollment.writeback_attempted_at
                        if time_since_last.total_seconds() < settings.writeback_retry_delay_seconds:
                            continue
                    
                    logger.info(f"Retrying enrollment {enrollment.enrollment_id} (attempt {enrollment.retry_count + 1})")
                    success, error_msg, resp_xml = await gateway.writeback_enrollment(enrollment)
                    
                    if success:
                        repo.update_enrollment_status(
                            enrollment.enrollment_id,
                            EnrollmentStatus.ENROLLED,
                            RetryStatus.RETRY_SUCCESS,
                            raw_response_xml=resp_xml,
                            target_enrollment_id=_extract_response_enrollment_id(resp_xml),
                        )
                        logger.info(f"Retry succeeded for {enrollment.enrollment_id}")
                    else:
                        repo.increment_retry_count(enrollment.enrollment_id)
                        logger.warning(f"Retry failed for {enrollment.enrollment_id}: {error_msg}")
                
                # 类似地处理待退选的记录
                pending_withdraws = repo.list_pending_withdraws()
                for enrollment in pending_withdraws:
                    if enrollment.retry_count >= settings.writeback_retry_max_attempts:
                        logger.warning(f"Withdrawal {enrollment.enrollment_id} exceeded max retry attempts")
                        continue
                    
                    logger.info(f"Retrying withdrawal {enrollment.enrollment_id}")
                    success, error_msg, resp_xml = await gateway.withdraw_enrollment(enrollment)
                    
                    if success:
                        repo.update_enrollment_status(
                            enrollment.enrollment_id,
                            EnrollmentStatus.WITHDRAWN,
                            RetryStatus.RETRY_SUCCESS,
                            raw_response_xml=resp_xml,
                        )
                        logger.info(f"Withdrawal succeeded for {enrollment.enrollment_id}")
                    else:
                        repo.increment_retry_count(enrollment.enrollment_id)
                        logger.warning(f"Withdrawal retry failed for {enrollment.enrollment_id}: {error_msg}")
                
                await asyncio.sleep(interval)
            
            except Exception as e:
                logger.error(f"Error in background retry task: {str(e)}")
                await asyncio.sleep(interval)
    
    # ==================== 生命周期 ====================
    
    @app.on_event("startup")
    async def startup():
        """启动事件"""
        logger.info("Integration Server starting up...")
        _app_state["background_tasks_running"] = True
        repo = get_repository(settings)
        gateway = get_gateway(settings)
        asyncio.create_task(_background_retry_task(repo, gateway))
        logger.info("Background retry task started")
    
    @app.on_event("shutdown")
    async def shutdown():
        """关闭事件"""
        logger.info("Integration Server shutting down...")
        _app_state["background_tasks_running"] = False
    
    # ==================== 健康检查 ====================
    
    @app.get("/health")
    async def health_check():
        """健康检查"""
        return {"status": "ok", "service": "integration-server"}
    
    # ==================== 共享课程接口 ====================
    
    @app.get("/api/v1/shared-courses")
    async def get_shared_courses(
        college_id: Optional[str] = None,
        collegeId: Optional[str] = None,
        gateway: CollegeGateway = Depends(get_gateway),
    ):
        """获取共享课程列表"""
        try:
            requested_college_id = college_id or collegeId
            shared_courses = await gateway.list_shared_courses(requested_college_id)
            if not shared_courses:
                shared_courses = [course.to_dict() for course in _get_mock_shared_courses(requested_college_id)]
            
            classes_data = {
                "class": shared_courses
            } if shared_courses else {"class": []}
            
            data = {
                "meta": {
                    "collegeId": requested_college_id or "ALL"
                },
                "classes": classes_data
            }
            if shared_courses:
                validate_xml_fragment("classes", classes_data, Path(__file__).parent / "xsd" / "formatClass.xsd")
            
            return xml_response(0, "success", data)
        
        except Exception as e:
            logger.error(f"Error in get_shared_courses: {str(e)}")
            return xml_response(500, f"Server error: {str(e)}")
    
    # ==================== 选课接口 ====================
    
    @app.post("/api/v1/enrollments")
    async def submit_enrollment(
        request: Request,
        repo: IntegrationRepository = Depends(get_repository),
        gateway: CollegeGateway = Depends(get_gateway),
    ):
        """提交选课请求"""
        try:
            # 读取请求体（XML）
            body = await request.body()
            xml_content = body.decode("utf-8")
            
            logger.debug(f"Received enrollment request:\n{xml_content[:500]}")
            
            # 解析 XML
            parsed = parse_xml(xml_content)
            request_data = parsed.get("EnrollmentRequest", {})
            
            # 提取信息
            meta = request_data.get("meta", {})
            home_college_id = get_text(meta, "homeCollegeId", "").upper() or "C"
            target_college_id = get_text(meta, "targetCollegeId", "").upper() or "A"
            
            # 提取 choices
            choices = request_data.get("choices", {})
            validate_xml_fragment("choices", choices, Path(__file__).parent / "xsd" / "formatClassChoice.xsd")
            choice = choices.get("choice", {}) if isinstance(choices, dict) else {}
            
            if not choice:
                logger.warning("No choice found in request")
                return xml_response(400, "missing choice data")
            
            student_id = get_text(choice, "sid", "").strip()
            course_id = get_text(choice, "cid", "").strip()
            score = int(get_text(choice, "score", "0") or "0")
            
            if not student_id or not course_id:
                logger.warning(f"Missing student_id or course_id: sid={student_id}, cid={course_id}")
                return xml_response(400, "missing sid or cid")
            
            logger.info(f"Processing enrollment: student={student_id}, course={course_id}, target={target_college_id}")
            
            # 检查是否已存在（幂等性）
            existing = repo.get_enrollment(student_id, course_id, target_college_id)
            if existing and existing.status != EnrollmentStatus.WITHDRAWN:
                logger.warning(f"Duplicate enrollment: {student_id} for {course_id}")
                return xml_response(
                    409,
                    "duplicate enrollment",
                    {
                        "enrollmentId": existing.enrollment_id,
                        "status": existing.status.value,
                    }
                )
            
            # 生成选课 ID
            enrollment_id = _generate_enrollment_id()
            
            # 创建记录
            enrollment = EnrollmentRecord(
                enrollment_id=enrollment_id,
                home_college_id=home_college_id,
                target_college_id=target_college_id,
                student_id=student_id,
                course_id=course_id,
                score=score,
                status=EnrollmentStatus.PENDING_WRITEBACK,
                raw_request_xml=xml_content,
            )
            
            # 保存到数据库
            created_id = repo.create_enrollment(enrollment)
            logger.info(f"Created enrollment record: {created_id}")
            
            # 先同步尝试一次写回；失败记录会进入后台重试队列。
            await _attempt_writeback(created_id, repo, gateway)
            
            # 返回响应
            data = {
                "enrollmentId": created_id,
                "status": EnrollmentStatus.PENDING_WRITEBACK.value,
                "targetCollegeId": target_college_id,
            }
            
            return xml_response(0, "enrollment accepted", data)
        
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return xml_response(400, f"Bad request: {str(e)}")
        except Exception as e:
            logger.error(f"Error in submit_enrollment: {str(e)}", exc_info=True)
            return xml_response(500, f"Server error: {str(e)}")
    
    # ==================== 退选接口 ====================
    
    @app.post("/api/v1/enrollments/{enrollment_id}/withdraw")
    async def withdraw_enrollment(
        enrollment_id: str,
        request: Request,
        repo: IntegrationRepository = Depends(get_repository),
        gateway: CollegeGateway = Depends(get_gateway),
    ):
        """退选请求"""
        try:
            # 查找选课记录
            enrollment = repo.get_enrollment_by_id(enrollment_id)
            if not enrollment:
                logger.warning(f"Enrollment not found: {enrollment_id}")
                return xml_response(404, "enrollment not found", {"enrollmentId": enrollment_id})
            
            if enrollment.status == EnrollmentStatus.WITHDRAWN:
                logger.info(f"Enrollment already withdrawn: {enrollment_id}")
                return xml_response(200, "withdraw writeback success", {
                    "enrollmentId": enrollment_id,
                    "status": "WITHDRAWN",
                })
            
            logger.info(f"Processing withdrawal for enrollment {enrollment_id}")
            
            # 更新状态为待退选
            repo.update_enrollment_status(
                enrollment_id,
                EnrollmentStatus.WITHDRAW_PENDING,
            )
            
            # 先同步尝试一次退选写回；失败记录会进入后台重试队列。
            await _attempt_withdraw(enrollment_id, repo, gateway)
            
            data = {
                "enrollmentId": enrollment_id,
                "status": "WITHDRAW_PENDING",
            }
            
            return xml_response(0, "withdraw accepted", data)
        
        except Exception as e:
            logger.error(f"Error in withdraw_enrollment: {str(e)}", exc_info=True)
            return xml_response(500, f"Server error: {str(e)}")
    
    async def _attempt_withdraw(enrollment_id: str, repo: IntegrationRepository, gateway: CollegeGateway):
        """尝试退选（后台任务）"""
        enrollment = repo.get_enrollment_by_id(enrollment_id)
        if not enrollment:
            logger.warning(f"Enrollment {enrollment_id} not found for withdrawal")
            return
        
        logger.info(f"Attempting withdrawal for enrollment {enrollment_id}")
        
        success, error_message, response_xml = await gateway.withdraw_enrollment(enrollment)
        
        if success:
            repo.update_enrollment_status(
                enrollment_id,
                EnrollmentStatus.WITHDRAWN,
                RetryStatus.RETRY_SUCCESS,
                raw_response_xml=response_xml,
            )
            logger.info(f"Withdrawal succeeded for enrollment {enrollment_id}")
        else:
            repo.increment_retry_count(enrollment_id)
            repo.update_enrollment_status(
                enrollment_id,
                EnrollmentStatus.WITHDRAW_PENDING,
                RetryStatus.RETRYING,
                error_message=error_message,
                raw_response_xml=response_xml,
            )
            logger.error(f"Withdrawal failed for enrollment {enrollment_id}: {error_message}")
    
    # ==================== 统计接口 ====================
    
    @app.get("/api/v1/stats/summary")
    async def get_stats_summary(
        request: Request,
        repo: IntegrationRepository = Depends(get_repository),
    ):
        """获取统计汇总"""
        try:
            if not _verify_api_key(request):
                return xml_response(401, "unauthorized")
            stats = repo.get_stats()
            gateway = get_gateway(settings)
            live_summary = await gateway.get_live_college_summary()
            
            # 补充三院统计（包括可能没有的学院）
            colleges = ["A", "B", "C"]
            college_list = []
            total_enrollments = 0
            total_students = 0
            total_courses = 0
            
            for college_id in colleges:
                college_stat = stats.get(college_id, {
                    "college_id": college_id,
                    "total_enrollments": 0,
                    "enrolled_count": 0,
                    "student_count": 0,
                    "course_count": 0,
                    "incoming_enrollments": 0,
                    "shared_course_count": 0,
                })
                live_college_stat = live_summary.get(college_id, {})
                merged_course_count = live_college_stat.get("course_count", college_stat.get("course_count", 0))
                merged_shared_count = live_college_stat.get("shared_course_count", college_stat.get("shared_course_count", 0))
                college_list.append({
                    "collegeId": college_id,
                    "studentCount": college_stat.get("student_count", 0),
                    "courseCount": merged_course_count,
                    "enrollmentCount": college_stat.get("total_enrollments", 0),
                    "enrolledCount": college_stat.get("enrolled_count", 0),
                    "incomingEnrollments": college_stat.get("incoming_enrollments", 0),
                    "sharedCourseCount": merged_shared_count,
                })
                total_enrollments += college_stat.get("total_enrollments", 0)
                total_students += college_stat.get("student_count", 0)
                total_courses += merged_course_count
            
            data = {
                "Summary": {
                    "college": college_list,
                    "total": {
                        "enrollmentCount": total_enrollments,
                        "studentCount": total_students,
                        "courseCount": total_courses,
                    }
                }
            }
            
            return xml_response(0, "success", data)
        
        except Exception as e:
            logger.error(f"Error in get_stats_summary: {str(e)}", exc_info=True)
            return xml_response(500, f"Server error: {str(e)}")
    
    # ==================== 管理接口 ====================
    
    @app.get("/api/v1/enrollments/{enrollment_id}")
    async def get_enrollment_detail(
        enrollment_id: str,
        request: Request,
        repo: IntegrationRepository = Depends(get_repository),
    ):
        """获取选课详情"""
        try:
            if not _verify_api_key(request):
                return xml_response(401, "unauthorized")
            enrollment = repo.get_enrollment_by_id(enrollment_id)
            if not enrollment:
                return xml_response(404, "enrollment not found")
            
            data = enrollment.to_dict()
            return xml_response(0, "success", {"enrollment": data})
        
        except Exception as e:
            logger.error(f"Error in get_enrollment_detail: {str(e)}")
            return xml_response(500, f"Server error: {str(e)}")

    return app


def _get_mock_shared_courses(college_id: Optional[str] = None) -> list[SharedCourse]:
    """获取 Mock 共享课程数据"""
    all_courses = [
        SharedCourse(id="A001", name="数据库系统", time=32, score=3, teacher="张老师", location="1-301", college_id="A"),
        SharedCourse(id="A002", name="数据挖掘", time=24, score=2, teacher="李老师", location="1-302", college_id="A"),
        SharedCourse(id="A003", name="数仓基础", time=24, score=2, teacher="王老师", location="3-105", college_id="A"),
        SharedCourse(id="B001", name="分布式系统", time=32, score=3, teacher="周老师", location="B-201", college_id="B"),
        SharedCourse(id="B002", name="机器学习基础", time=24, score=2, teacher="吴老师", location="B-305", college_id="B"),
        SharedCourse(id="C001", name="软件工程实践", time=32, score=3, teacher="陈老师", location="C-401", college_id="C"),
        SharedCourse(id="C023", name="XML 数据交换", time=16, score=2, teacher="王老师", location="3-102", college_id="C"),
    ]
    
    if college_id:
        college_id = college_id.upper()
        return [c for c in all_courses if c.college_id == college_id]
    
    return all_courses
