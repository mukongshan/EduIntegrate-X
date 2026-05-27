#!/usr/bin/env python
"""启动集成服务器"""
import sys
import uvicorn
from integration_server.app import create_app
from integration_server.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    app = create_app(settings)
    
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
