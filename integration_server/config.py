"""集成服务器配置"""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """集成服务器配置"""
    
    # 基础配置
    app_name: str = "EduIntegrate Integration Server"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8081
    
    # 数据库配置
    db_path: str = "./integration_server.db"
    
    # 学院服务配置（用于回写）
    college_a_url: str = "http://localhost:8000"
    college_b_url: str = "http://localhost:8001"
    college_c_url: str = "http://localhost:8002"
    
    # API Key（简单认证）
    api_key: str = "integration-server-api-key-2026"
    
    # 重试配置
    writeback_retry_max_attempts: int = 3
    writeback_retry_delay_seconds: int = 5
    
    # 共享课程配置（Mock数据）
    shared_courses_catalog: str = "A,B,C"

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_flag(cls, value):
        """兼容 DEBUG=release/dev 这类运行环境写法。"""
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"dev", "development"}:
                return True
        return value
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """获取配置（单例缓存）"""
    return Settings()
