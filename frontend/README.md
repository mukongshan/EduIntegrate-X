# EduIntegrate Frontend

前端是学院门户和集成统计页，默认用于本机真实联调演示：登录/本院课程直连学院后端，共享课程/跨院选课/退选/我的选课/统计直连集成服务器。

完整演示环境启动后，A/B/C 每院都有 50 个学生、10 门课程、250 条本院选课记录，统计页会展示三院汇总。

## 快速启动

推荐从仓库根目录启动完整演示：

```bash
./scripts/install_demo_deps.sh
./scripts/dev_up.sh
```

只启动前端：

```bash
cd frontend
npm install
npm run dev
```

## 环境配置

Vite 已配置为读取仓库根目录 `.env`。

```env
VITE_USE_MOCK=false
VITE_API_URL_A=http://localhost:8000
VITE_API_URL_B=http://localhost:8001
VITE_API_URL_C=http://localhost:8002
VITE_API_URL_INTEGRATION=http://localhost:8081
VITE_INTEGRATION_API_KEY=integration-server-api-key-2026
```

`VITE_USE_MOCK=true` 时使用浏览器内存 mock，仅用于界面预览。作业演示请使用 `false`。

## 后端接口

| 接口 | 方法 | 说明 | 目标 |
| --- | --- | --- | --- |
| `/api/v1/auth/login` | POST | 登录 | 当前学院后端 |
| `/api/v1/courses` | GET | 本院课程 | 当前学院后端 |
| `/api/v1/shared-courses` | GET | 共享课程 | 集成服务器 |
| `/api/v1/enrollments` | POST | 跨院选课 | 集成服务器 |
| `/api/v1/students/{sid}/enrollments` | GET | 我的选课 | 集成服务器 |
| `/api/v1/enrollments/{id}/withdraw` | POST | 退选 | 集成服务器 |
| `/api/v1/stats/summary` | GET | 统计汇总 | 集成服务器，需带演示 API Key |

真实联调模式下，选课/退选失败会返回错误状态，不再伪造成功结果。
