# EduIntegrate-X 本机演示交付说明

EduIntegrate-X 是一个基于 XML 的异构教务系统集成示例。仓库包含学院 A/B/C 后端、数据集成服务器和 React 前端。本交付默认使用 mock 数据跑通作业演示闭环，不依赖 SQL Server、Oracle 或 MySQL。

每个学院默认生成 50 个学生、10 门课程、250 条本院选课记录；同时提供 SQL Server、Oracle、MySQL 三套真实库导入 SQL。

## 一键演示

安装依赖：

```bash
./scripts/install_demo_deps.sh
```

启动五个服务：

```bash
./scripts/dev_up.sh
```

启动脚本会重置集成服务器演示库，并重新生成 `data/generated/college_a_demo.sql`、`college_b_demo.sql`、`college_c_demo.sql`。

验收联调闭环：

```bash
./scripts/smoke_test.sh
```

停止服务：

```bash
./scripts/dev_down.sh
```

## 服务端口

| 服务 | 地址 |
| --- | --- |
| 学院 A 后端 | `http://localhost:8000` |
| 学院 B 后端 | `http://localhost:8001` |
| 学院 C 后端 | `http://localhost:8002` |
| 集成服务器 | `http://localhost:8081` |
| 前端 | `http://localhost:5173` |

日志位于 `logs/`，进程号位于 `tmp/dev_pids/`，集成服务器演示数据库位于 `tmp/integration_server_demo.db`。

## 演示账号

| 学院 | 账号 | 密码 |
| --- | --- | --- |
| A | `a_student1` | `123456` |
| B | `b_student1` | `123456` |
| C | `c_student1` | `123456` |

## 数据与报告

- 统一数据生成器：`demo_data.py`
- SQL 生成脚本：`scripts/generate_demo_sql.py`
- 真实库 SQL 输出：`data/generated/`
- 最终报告：`docs/作业3最终报告.md`
- Smoke test 会断言三院 `50/10/250` 规模，以及集成统计总计 `150/30/750`。

## 手工演示路径

1. 打开 `http://localhost:5173/college/A/login`。
2. 使用 `a_student1 / 123456` 登录。
3. 进入课程列表，切到“共享课程”。
4. 选择 `B001` 或其他 B/C 学院共享课。
5. 打开“我的选课”，确认记录已出现。
6. 点击退选，确认记录移除。
7. 打开 `http://localhost:5173/integration` 查看统计。

## 联调链路

- 前端登录和本院课程查询直连当前学院后端。
- 前端共享课程、跨院选课、退选、我的选课、统计直连集成服务器。
- 集成服务器通过 XML 调用目标学院的内部写回接口。
- 共享课程响应包含 `collegeId`，用于判断课程属于哪个学院。

## 环境变量

前端真实联调使用仓库根目录 `.env`，可从 `.env.example` 复制：

```bash
cp .env.example .env
```

本机演示关键变量：

```env
VITE_USE_MOCK=false
VITE_API_URL_A=http://localhost:8000
VITE_API_URL_B=http://localhost:8001
VITE_API_URL_C=http://localhost:8002
VITE_API_URL_INTEGRATION=http://localhost:8081
VITE_INTEGRATION_API_KEY=integration-server-api-key-2026
```

真实数据库适配代码仍保留在 A/B/C 后端中，但不属于默认 smoke test 的依赖。
