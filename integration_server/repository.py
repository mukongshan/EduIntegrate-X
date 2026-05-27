"""集成服务器数据仓库（SQLite）"""
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import EnrollmentRecord, EnrollmentStatus, RetryStatus


class IntegrationRepository:
    """集成服务器持久化层"""
    
    def __init__(self, db_path: str = "./integration_server.db"):
        """初始化数据库"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            # 选课记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS enrollments (
                    enrollment_id TEXT PRIMARY KEY,
                    home_college_id TEXT NOT NULL,
                    target_college_id TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    course_id TEXT NOT NULL,
                    score INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'PENDING_WRITEBACK',
                    retry_status TEXT DEFAULT 'NOT_RETRIED',
                    retry_count INTEGER DEFAULT 0,
                    raw_request_xml TEXT,
                    raw_response_xml TEXT,
                    target_enrollment_id TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    writeback_attempted_at TIMESTAMP
                )
            """)
            cursor.execute("PRAGMA table_info(enrollments)")
            columns = {row[1] for row in cursor.fetchall()}
            if "target_enrollment_id" not in columns:
                cursor.execute("ALTER TABLE enrollments ADD COLUMN target_enrollment_id TEXT")
            # 创建复合唯一约束（同一学生同一课程）
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_enrollment 
                ON enrollments(student_id, course_id, target_college_id) 
                WHERE status != 'WITHDRAWN'
            """)
            # 创建查询索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON enrollments(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_college ON enrollments(home_college_id, target_college_id)
            """)
            conn.commit()
    
    def create_enrollment(self, enrollment_record: EnrollmentRecord) -> str:
        """创建选课记录"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO enrollments (
                        enrollment_id, home_college_id, target_college_id, student_id, course_id,
                        score, status, retry_status, retry_count, raw_request_xml, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    enrollment_record.enrollment_id,
                    enrollment_record.home_college_id,
                    enrollment_record.target_college_id,
                    enrollment_record.student_id,
                    enrollment_record.course_id,
                    enrollment_record.score,
                    enrollment_record.status.value,
                    enrollment_record.retry_status.value,
                    enrollment_record.retry_count,
                    enrollment_record.raw_request_xml,
                    enrollment_record.created_at,
                    enrollment_record.updated_at,
                ))
                conn.commit()
                return enrollment_record.enrollment_id
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed" in str(e):
                    # 返回已存在的记录
                    existing = self.get_enrollment(enrollment_record.student_id, enrollment_record.course_id)
                    if existing:
                        return existing.enrollment_id
                raise
    
    def get_enrollment(self, student_id: str, course_id: str, target_college_id: str = None) -> Optional[EnrollmentRecord]:
        """获取选课记录（按学生和课程）"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if target_college_id:
                cursor.execute("""
                    SELECT * FROM enrollments 
                    WHERE student_id = ? AND course_id = ? AND target_college_id = ?
                    AND status != 'WITHDRAWN'
                    LIMIT 1
                """, (student_id, course_id, target_college_id))
            else:
                cursor.execute("""
                    SELECT * FROM enrollments 
                    WHERE student_id = ? AND course_id = ?
                    AND status != 'WITHDRAWN'
                    LIMIT 1
                """, (student_id, course_id))
            row = cursor.fetchone()
            if row:
                return self._row_to_enrollment(row)
            return None
    
    def get_enrollment_by_id(self, enrollment_id: str) -> Optional[EnrollmentRecord]:
        """按 ID 获取选课记录"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM enrollments WHERE enrollment_id = ?", (enrollment_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_enrollment(row)
            return None
    
    def update_enrollment_status(
        self, 
        enrollment_id: str, 
        status: EnrollmentStatus,
        retry_status: RetryStatus = None,
        error_message: str = None,
        raw_response_xml: str = None,
        target_enrollment_id: str = None,
    ) -> bool:
        """更新选课记录状态"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            updates = ["status = ?"]
            params = [status.value]
            
            if retry_status:
                updates.append("retry_status = ?")
                params.append(retry_status.value)
            
            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)
            
            if raw_response_xml is not None:
                updates.append("raw_response_xml = ?")
                params.append(raw_response_xml)

            if target_enrollment_id is not None:
                updates.append("target_enrollment_id = ?")
                params.append(target_enrollment_id)
            
            updates.append("updated_at = ?")
            params.append(datetime.now())
            
            params.append(enrollment_id)
            
            query = f"UPDATE enrollments SET {', '.join(updates)} WHERE enrollment_id = ?"
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
    
    def increment_retry_count(self, enrollment_id: str) -> bool:
        """增加重试次数"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE enrollments 
                SET retry_count = retry_count + 1, 
                    writeback_attempted_at = ?,
                    updated_at = ?
                WHERE enrollment_id = ?
            """, (datetime.now(), datetime.now(), enrollment_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def list_pending_writebacks(self) -> list[EnrollmentRecord]:
        """列出待写回的记录"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM enrollments 
                WHERE status IN ('PENDING_WRITEBACK', 'WRITEBACK_FAILED')
                ORDER BY created_at ASC
                LIMIT 100
            """)
            rows = cursor.fetchall()
            return [self._row_to_enrollment(row) for row in rows]
    
    def list_pending_withdraws(self) -> list[EnrollmentRecord]:
        """列出待退选的记录"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM enrollments 
                WHERE status = 'WITHDRAW_PENDING'
                ORDER BY created_at ASC
                LIMIT 100
            """)
            rows = cursor.fetchall()
            return [self._row_to_enrollment(row) for row in rows]
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 按学院统计
            cursor.execute("""
                SELECT target_college_id, 
                       COUNT(*) as total_enrollments,
                       SUM(CASE WHEN status = 'ENROLLED' THEN 1 ELSE 0 END) as enrolled_count,
                       COUNT(DISTINCT student_id) as student_count,
                       COUNT(DISTINCT course_id) as course_count
                FROM enrollments
                WHERE status != 'WITHDRAWN'
                GROUP BY target_college_id
            """)
            stats = {}
            for row in cursor.fetchall():
                college_id = row["target_college_id"]
                stats[college_id] = {
                    "college_id": college_id,
                    "total_enrollments": row["total_enrollments"],
                    "enrolled_count": row["enrolled_count"],
                    "student_count": row["student_count"],
                    "course_count": row["course_count"],
                    "incoming_enrollments": row["enrolled_count"],  # 简化：认为 enrolled 就是 incoming
                    "shared_course_count": row["course_count"],
                }
            
            return stats
    
    def _row_to_enrollment(self, row: sqlite3.Row) -> EnrollmentRecord:
        """将数据库行转换为对象"""
        return EnrollmentRecord(
            enrollment_id=row["enrollment_id"],
            home_college_id=row["home_college_id"],
            target_college_id=row["target_college_id"],
            student_id=row["student_id"],
            course_id=row["course_id"],
            score=row["score"],
            status=EnrollmentStatus(row["status"]),
            retry_status=RetryStatus(row["retry_status"]),
            retry_count=row["retry_count"],
            raw_request_xml=row["raw_request_xml"] or "",
            raw_response_xml=row["raw_response_xml"] or "",
            target_enrollment_id=row["target_enrollment_id"],
            error_message=row["error_message"],
            created_at=datetime.fromisoformat(row["created_at"]) if isinstance(row["created_at"], str) else row["created_at"],
            updated_at=datetime.fromisoformat(row["updated_at"]) if isinstance(row["updated_at"], str) else row["updated_at"],
            writeback_attempted_at=datetime.fromisoformat(row["writeback_attempted_at"]) if row["writeback_attempted_at"] and isinstance(row["writeback_attempted_at"], str) else row["writeback_attempted_at"],
        )
