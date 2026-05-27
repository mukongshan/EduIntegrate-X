# EduIntegrate Frontend (MVP)

## 快速启动

```bash
cd frontend
npm install
# 方式一：使用 mock server（开发预览用）
npm run mock    # 启动 mock 后端在 localhost:8081
npm run dev     # 启动前端在 localhost:5173

# 方式二：连接真实后端（联调/部署用）
# 修改 .env 文件（见下方配置说明），然后
npm run dev
```

## 环境配置说明

前端通过环境变量决定使用 mock 还是真实后端，配置文件为 `.env`（根目录）。

```bash
# .env 示例
VITE_USE_MOCK=false                              # false=真实后端，true=浏览器内mock
VITE_API_URL_INTEGRATION=http://localhost:8081   # 集成服务器地址（必填）
VITE_API_URL_A=http://localhost:8085             # 学院A后端地址
VITE_API_URL_B=http://localhost:8085             # 学院B后端地址
VITE_API_URL_C=http://localhost:8085             # 学院C后端地址
```

### mock 与真实后端的切换

- `VITE_USE_MOCK=true`：所有数据来自浏览器内存的 mock，不发真实请求（仅用于预览）
- `VITE_USE_MOCK=false`：所有 API 调用发到真实后端；后端不可用时会 fallback 到 mock 保底

## 后端接口要求

前端期望后端实现以下接口（详细说明见 `/docs/API协议与联调说明.md`）：

| 接口                                 | 方法 | 说明             | 路由解析                   |
| ------------------------------------ | ---- | ---------------- | -------------------------- |
| `/api/v1/shared-courses`             | GET  | 获取共享课程列表 | → VITE_API_URL_INTEGRATION |
| `/api/v1/college/{A\|B\|C}/courses`  | GET  | 获取本院课程     | → VITE_API_URL_A/B/C       |
| `/api/v1/auth/login`                 | POST | 登录验证         | → VITE_API_URL_INTEGRATION |
| `/api/v1/enrollments`                | POST | 提交选课         | → VITE_API_URL_INTEGRATION |
| `/api/v1/students/{sid}/enrollments` | GET  | 获取学生选课列表 | → VITE_API_URL_INTEGRATION |
| `/api/v1/enrollments/{id}/withdraw`  | POST | 退选             | → VITE_API_URL_INTEGRATION |
| `/api/v1/stats/summary`              | GET  | 统计汇总         | → VITE_API_URL_INTEGRATION |

**重要**：前端通过 URL 路径自动判断发到哪个后端：
- 包含 `/college/` 的路径 → 打到对应学院后端（A/B/C）
- 其余 `/api/v1/...` 路径 → 打到集成服务器（INTEGRATION）

## 开发注意事项

- 开发时后端地址使用 `localhost`；部署时替换为内网地址（如 `10.60.254.43:8081`）
- 不要在代码中硬编码后端地址，统一使用环境变量
- 切换 mock/真实后端后需**重启 dev server** 才能生效
