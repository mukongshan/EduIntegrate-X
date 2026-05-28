# College B Backend README

本目录是学院 B 教务系统后端实现，接口风格与学院 A 保持一致，默认使用内存数据方便本地演示；设置 `COLLEGE_B_STORAGE=oracle` 后可切换到 Oracle。

## 运行

```bash
python -m pip install -r college_b/requirements.txt
python -m uvicorn college_b.app.main:create_app --factory --host 0.0.0.0 --port 8001
```

## Oracle 配置

```env
COLLEGE_B_STORAGE=oracle
COLLEGE_ID=B
ORACLE_DSN=localhost:1521/XEPDB1
ORACLE_USER=collegeb_user
ORACLE_PASSWORD=CollegeB123
```

启动时会自动创建 `Account`、`Student`、`Course`、`Enrollment`、`EnrollmentLog`、`OutboundRequestLog`，并写入少量演示数据。手工建表 SQL 位于 `college_b/data/db/create_tables.sql`。

## 主要接口

- `POST /api/v1/auth/login`
- `GET /api/v1/courses`
- `GET /api/v1/students/{student_id}`
- `GET /api/v1/shared-courses?collegeId=B`
- `POST /api/v1/enrollments`
- `POST /api/v1/enrollments/{enrollment_id}/withdraw`
- `POST /internal/v1/enrollments/writeback`
- `POST /internal/v1/enrollments/withdraw`
