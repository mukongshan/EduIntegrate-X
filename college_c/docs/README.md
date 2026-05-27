# College C Backend README

## 1. 项目说明

本目录是学院 C 后端服务实现，面向作业中的 MySQL 学院系统。接口风格与学院 A 保持一致，统一使用 XML 请求与 XML 响应，便于后续接入集成服务器。

当前支持两种运行模式：

- `mock`：使用内存数据，适合本地快速调试和演示。
- `mysql`：连接真实 MySQL，适合联调和真实写库验证。

当前已实现：

- 登录接口，兼容 C 学院字段 `acc/passwd`。
- 本院课程查询接口，输出统一课程 XML 字段。
- 学生信息查询接口。
- 共享课程查询接口，当前使用 mock 集成服务器。
- 本院选课接口。
- 跨院选课 mock 转发接口。
- 集成服务器选课写回接口。
- 集成服务器退选写回接口。

## 2. 目录结构

```text
college_c/
  app/
    config.py
    integration.py
    main.py
    models.py
    mysql_repository.py
    repository.py
    xml_utils.py
  docs/
    README.md
  tests/
    test_app.py
    test_real_mysql.py
  requirements.txt
```

## 3. 环境准备

建议准备：

- Python 3.12
- MySQL 8.0 或兼容版本

安装依赖：

```powershell
python -m pip install -r college_c/requirements.txt
```

## 4. 配置方式

配置放在仓库根目录 `.env`，不要提交真实凭据。

mock 模式最小配置：

```env
COLLEGE_C_STORAGE=mock
COLLEGE_C_ID=C
COLLEGE_C_PORT=8002
```

MySQL 模式示例：

```env
COLLEGE_C_STORAGE=mysql
COLLEGE_C_ID=C
COLLEGE_C_PORT=8002

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=CollegeC_DB
MYSQL_USER=collegec_user
MYSQL_PASSWORD=CollegeC@123
MYSQL_CHARSET=utf8mb4

RUN_MYSQL_TESTS=1
COLLEGE_C_TEST_DATABASE=CollegeC_DB
```

## 5. 启动服务

```powershell
python -m uvicorn college_c.app.main:create_app --factory --host 0.0.0.0 --port 8002
```

健康检查：

```powershell
curl http://127.0.0.1:8002/health
```

预期返回：

```json
{"status":"ok"}
```

## 6. 接口清单

- `GET /health`
- `POST /api/v1/auth/login`
- `GET /api/v1/courses`
- `GET /api/v1/students/{student_id}`
- `GET /api/v1/shared-courses`
- `POST /api/v1/enrollments`
- `POST /api/v1/enrollments/{enrollmentId}/withdraw`
- `POST /internal/v1/enrollments/writeback`
- `POST /internal/v1/enrollments/withdraw`

登录请求示例：

```xml
<LoginRequest>
  <acc>c_student1</acc>
  <passwd>123456</passwd>
</LoginRequest>
```

选课写回请求示例：

```xml
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
```

## 7. 测试

mock 测试：

```powershell
python -m pytest college_c/tests/test_app.py -q
```

真实 MySQL 测试：

```powershell
python -m pytest college_c/tests/test_real_mysql.py -q
```

真实 MySQL 测试默认跳过，只有 `RUN_MYSQL_TESTS=1` 且 MySQL 配置完整时才执行。
