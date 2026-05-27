# 集成服务器（Integration Server）

## 概述

集成服务器是 EduIntegrate-X 数据集成系统的核心组件，负责：

- **共享课程汇总**：聚合三院的可共享课程
- **跨院选课协调**：处理学生跨院选课请求，并将选课结果写回原课程所在学院
- **选课回写管理**：处理同步失败、重试和幂等性
- **统计汇总**：提供三院学生、课程与选课的统计数据

## 技术栈

- **框架**：FastAPI + Uvicorn
- **数据库**：SQLite（MVP）
- **XML处理**：xmltodict + lxml
- **HTTP客户端**：httpx
- **异步任务**：asyncio

## 项目结构

```
integration_server/
├── __init__.py
├── app.py                 # FastAPI 主应用
├── config.py             # 配置类
├── models.py             # 数据模型
├── repository.py         # SQLite 持久化层
├── gateway.py            # 学院交互网关
├── xml_utils.py          # XML 工具函数
├── xsd/                  # XML Schema 定义
│   ├── formatClass.xsd
│   ├── formatStudent.xsd
│   └── formatClassChoice.xsd
├── xsl/                  # XSLT 转换模板
│   ├── writeback_to_A.xsl
│   ├── writeback_to_B.xsl
│   ├── writeback_to_C.xsl
│   ├── withdraw_to_A.xsl
│   ├── withdraw_to_B.xsl
│   └── withdraw_to_C.xsl
├── tests/                # 单元与集成测试
│   ├── __init__.py
│   └── test_integration_server.py
├── requirements.txt      # 依赖清单
├── README.md            # 本文件
└── .env.example         # 环境变量示例
```

## 快速开始

### 1. 安装依赖

```bash
cd integration_server
pip install -r requirements.txt
```

### 2. 配置环境

创建 `.env` 文件（或使用 `.env.example` 作为模板）：

```bash
# 基本配置
APP_NAME=EduIntegrate Integration Server
DEBUG=False
LOG_LEVEL=INFO

# 服务配置
HOST=0.0.0.0
PORT=8081

# 数据库
DB_PATH=./integration_server.db

# 学院服务 URL（用于回写）
COLLEGE_A_URL=http://localhost:8000
COLLEGE_B_URL=http://localhost:8001
COLLEGE_C_URL=http://localhost:8002

# API Key（简单认证）
API_KEY=integration-server-api-key-2026

# 重试配置
WRITEBACK_RETRY_MAX_ATTEMPTS=3
WRITEBACK_RETRY_DELAY_SECONDS=5
```

### 3. 运行服务

**开发模式（带自动重载）**：

```bash
uvicorn integration_server.app:create_app --host 0.0.0.0 --port 8081 --reload
```

**生产模式**：

```bash
uvicorn integration_server.app:create_app --host 0.0.0.0 --port 8081
```

或使用启动脚本：

```bash
python run.py
```

### 4. 验证服务

```bash
# 健康检查
curl http://localhost:8081/health

# 查询共享课程
curl http://localhost:8081/api/v1/shared-courses

# 获取统计汇总
curl http://localhost:8081/api/v1/stats/summary
```

## API 端点

### 共享课程

**GET /api/v1/shared-courses**

查询可共享的课程列表。

请求：

```http
GET /api/v1/shared-courses?college_id=A HTTP/1.1
Accept: application/xml
```

响应（成功）：

```xml
<Response>
  <code>0</code>
  <message>success</message>
  <data>
    <meta>
      <collegeId>A</collegeId>
    </meta>
    <classes>
      <class>
        <id>C001</id>
        <name>数据库系统</name>
        <time>32</time>
        <score>3</score>
        <teacher>张老师</teacher>
        <location>1-301</location>
      </class>
      ...
    </classes>
  </data>
</Response>
```

### 提交选课

**POST /api/v1/enrollments**

提交跨院选课请求。

请求：

```xml
<?xml version="1.0" encoding="UTF-8"?>
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
</EnrollmentRequest>
```

响应（成功）：

```xml
<Response>
  <code>0</code>
  <message>enrollment accepted</message>
  <data>
    <enrollmentId>E20260527102030ABC12345</enrollmentId>
    <status>PENDING_WRITEBACK</status>
    <targetCollegeId>A</targetCollegeId>
  </data>
</Response>
```

响应（重复）：

```xml
<Response>
  <code>409</code>
  <message>duplicate enrollment</message>
  <data>
    <enrollmentId>E20260527102030ABC12345</enrollmentId>
    <status>EXISTS</status>
  </data>
</Response>
```

### 退选课程

**POST /api/v1/enrollments/{enrollmentId}/withdraw**

退选已选课程。

请求：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<WithdrawRequest>
  <meta>
    <requestTime>2026-05-27 11:00:00</requestTime>
  </meta>
</WithdrawRequest>
```

响应（成功）：

```xml
<Response>
  <code>0</code>
  <message>withdraw accepted</message>
  <data>
    <enrollmentId>E20260527102030ABC12345</enrollmentId>
    <status>WITHDRAW_PENDING</status>
  </data>
</Response>
```

### 统计汇总

**GET /api/v1/stats/summary**

获取三院学生、课程与选课的汇总统计。

请求头：

```http
Authorization: Bearer <api_key>
```

响应：

```xml
<Response>
  <code>0</code>
  <message>success</message>
  <data>
    <Summary>
      <college>
        <collegeId>A</collegeId>
        <studentCount>50</studentCount>
        <courseCount>10</courseCount>
        <enrollmentCount>250</enrollmentCount>
        <sharedCourseCount>2</sharedCourseCount>
        <incomingEnrollments>8</incomingEnrollments>
      </college>
      <college>
        <collegeId>B</collegeId>
        ...
      </college>
      <college>
        <collegeId>C</collegeId>
        ...
      </college>
      <total>
        <enrollmentCount>750</enrollmentCount>
        <studentCount>150</studentCount>
        <courseCount>30</courseCount>
      </total>
    </Summary>
  </data>
</Response>
```

## 数据库设计

### enrollments 表

```sql
CREATE TABLE enrollments (
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
);
```

**字段说明**：

- `enrollment_id`：选课记录的唯一标识（E + 时间戳 + 随机后缀）
- `status`：选课状态（PENDING_WRITEBACK、ENROLLED、WRITEBACK_FAILED、WITHDRAW_PENDING、WITHDRAWN）
- `retry_status`：重试状态（NOT_RETRIED、RETRYING、RETRY_SUCCESS、RETRY_FAILED）
- `retry_count`：已重试次数
- `raw_request_xml`：原始请求 XML（用于重试时重建请求）
- `raw_response_xml`：原始响应 XML（用于调试）
- `target_enrollment_id`：目标学院写回后返回的选课 ID（用于后续退选写回）
- `error_message`：错误信息（若有）

## 核心功能

### 1. 幂等性

当学生重复提交同一课程的选课请求时，系统会：

1. 查询数据库是否存在该学生对该课程的未撤销选课记录。
2. 若存在且状态不为 WITHDRAWN，返回 409 Conflict，并提供原始 enrollmentId。
3. 若不存在，生成新 enrollmentId 并创建记录。

### 2. 选课回写机制

当集成服务器收到选课请求后，会：

1. **同步尝试**：立即尝试向目标学院的 `/internal/v1/enrollments/writeback` 发起回写请求。
2. **异步重试**：如果同步失败，后台任务将在固定时间间隔后自动重试。
3. **重试限制**：最多重试 3 次（可配置），超过限制后标记为 RETRY_FAILED 并记录错误。

状态转移：

```
PENDING_WRITEBACK 
    ↓ (同步成功)
ENROLLED
    ↓ (同步失败)
WRITEBACK_FAILED 
    ↓ (后台重试成功)
ENROLLED
```

### 3. 退选处理

1. 收到退选请求后，更新选课状态为 WITHDRAW_PENDING。
2. 同步尝试向目标学院的 `/internal/v1/enrollments/withdraw` 发起退选通知，失败后进入后台重试。
3. 若成功，更新状态为 WITHDRAWN；若失败，进入重试流程。

### 4. 后台重试任务

后台任务每 30 秒扫描一次待重试的记录（PENDING_WRITEBACK 和 WRITEBACK_FAILED 状态），并尝试回写。

任务流程：

1. 查询所有待回写的记录。
2. 对于每条记录，检查上次尝试以来的时间是否超过 `writeback_retry_delay_seconds`。
3. 若是，发起回写请求并更新状态。
4. 记录失败信息，供后续调试。

## 学院系统写回接口规范

集成服务器需要能调用各学院系统的以下接口：

### 选课写回

**POST /internal/v1/enrollments/writeback**

请求头：

```http
Content-Type: application/xml
Authorization: Bearer <api_key>
```

请求体（XML）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<WritebackRequest>
  <meta>
    <sourceCollegeId>C</sourceCollegeId>
    <targetCollegeId>A</targetCollegeId>
    <status>ENROLLED</status>
    <requestTime>2026-05-27 10:30:00</requestTime>
  </meta>
  <choices>
    <choice>
      <sid>S2024001</sid>
      <cid>C001</cid>
      <score>0</score>
    </choice>
  </choices>
</WritebackRequest>
```

预期响应：

```xml
<Response>
  <code>0</code>
  <message>writeback success</message>
  <data>
    <enrollmentId>E20260527102030ABC12345</enrollmentId>
    <collegeId>A</collegeId>
    <status>ENROLLED</status>
  </data>
</Response>
```

### 退选写回

**POST /internal/v1/enrollments/withdraw**

请求头与选课写回相同。

请求体（XML）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<WithdrawWritebackRequest>
  <enrollmentId>E20260527102030ABC12345</enrollmentId>
  <studentId>S2024001</studentId>
  <courseId>C001</courseId>
  <status>WITHDRAWN</status>
</WithdrawWritebackRequest>
```

## 运行测试

### 单元测试

```bash
# 运行所有测试
pytest integration_server/tests/ -v

# 运行特定测试类
pytest integration_server/tests/test_integration_server.py::TestEnrollment -v

# 带覆盖率报告
pytest integration_server/tests/ --cov=integration_server --cov-report=html
```

### 集成测试（手动）

1. 启动集成服务器：

```bash
uvicorn integration_server.app:create_app --port 8081
```

2. 启动一个学院系统（如 college_a）：

```bash
cd college_a
uvicorn app.main:create_app --port 8000
```

3. 提交跨院选课请求：

```bash
curl -X POST http://localhost:8081/api/v1/enrollments \
  -H "Content-Type: application/xml" \
  -d @- <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<EnrollmentRequest>
  <meta>
    <homeCollegeId>C</homeCollegeId>
    <targetCollegeId>A</targetCollegeId>
  </meta>
  <choices>
    <choice>
      <sid>S2024001</sid>
      <cid>C001</cid>
      <score>0</score>
    </choice>
  </choices>
</EnrollmentRequest>
EOF
```

4. 查看选课记录状态：

```bash
curl http://localhost:8081/api/v1/enrollments/E<enrollment_id>
```

## Docker 部署

### 手动 Docker 构建

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY integration_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY integration_server/ ./integration_server/

EXPOSE 8081

CMD ["uvicorn", "integration_server.app:create_app", "--host", "0.0.0.0", "--port", "8081"]
```

构建并运行：

```bash
docker build -t integration-server .
docker run -p 8081:8081 integration-server
```

## 故障排查

### 连接超时

**症状**：选课回写失败，返回 "Request timeout" 或 "Connection failed"。

**原因**：目标学院服务不可用或网络不通。

**解决**：
- 检查学院服务是否启动：`curl http://localhost:8000/health`
- 检查网络连接：`ping <college-url>`
- 调整超时时间（在 config.py 中修改 `timeout`）

### 持久化问题

**症状**：重启后选课记录丢失。

**原因**：使用了内存数据库或数据库路径错误。

**解决**：
- 检查 `.env` 中的 `DB_PATH` 设置
- 确保数据库文件可写入
- 检查磁盘空间

### API Key 验证失败

**症状**：写回请求返回 401 Unauthorized。

**原因**：学院系统验证 API Key 失败。

**解决**：
- 确保 `.env` 中的 `API_KEY` 与学院系统配置一致
- 检查 Authorization header 格式：`Bearer <key>`

## 性能优化建议

### 1. 使用 PostgreSQL 替代 SQLite

对于生产环境，建议使用 PostgreSQL 以获得更好的并发性能和可靠性。

### 2. 添加缓存

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_shared_courses(college_id):
    # ...
```

### 3. 连接池

使用 httpx 的连接池或 sqlalchemy 的连接池管理数据库连接。

### 4. 异步任务队列

用 Celery + Redis 替代简单的 asyncio 任务，以获得更可靠的重试机制。

## 常见问题

**Q: 为什么写回请求有时候会返回 PENDING_WRITEBACK？**

A: 这是正常的。如果同步写回失败，集成服务器会立即返回 PENDING_WRITEBACK 状态，并在后台继续尝试。前端可以轮询 `/api/v1/enrollments/{enrollmentId}` 来获取最新状态。

**Q: 重试最多尝试几次？**

A: 默认配置为 3 次（`WRITEBACK_RETRY_MAX_ATTEMPTS=3`），可在 `.env` 中修改。

**Q: 能否关闭后台重试任务？**

A: 后台任务目前无法单独关闭，但可以通过设置 `WRITEBACK_RETRY_MAX_ATTEMPTS=1` 来限制重试次数。

## 许可证

MIT

## 联系方式

如有问题，请联系项目维护者。
