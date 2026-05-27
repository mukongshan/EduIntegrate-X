FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY integration_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY integration_server/ ./integration_server/

# 暴露端口
EXPOSE 8081

# 启动应用
CMD ["python", "-m", "uvicorn", "integration_server.app:create_app", "--host", "0.0.0.0", "--port", "8081"]
