"""
配置中心 - 使用 Pydantic Settings 管理配置
支持环境变量覆盖
"""
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List, Optional
import os


class Settings(BaseSettings):
    """应用配置"""
    
    # 基础配置
    APP_NAME: str = "AI智能测试大屏平台"
    VERSION: str = "2.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS 配置
    CORS_ORIGINS: List[str] = ["*"]
    
    # 数据库配置
    DATABASE_PATH: str = str(Path(__file__).parent.parent.parent.parent / "database" / "test_platform.db")
    
    # 设备配置
    MAX_DEVICES: int = 2
    DEVICE_HEARTBEAT_INTERVAL: int = 5  # 秒
    DEVICE_OFFLINE_THRESHOLD: int = 15  # 秒
    ADB_RECONNECT_ATTEMPTS: int = 3
    ADB_RECONNECT_DELAY: int = 2  # 秒
    ADB_PATH: str = "adb"  # ADB 可执行文件路径
    
    # AI 模型配置
    QWEN_MODEL_PATH: str = str(Path(__file__).parent.parent.parent.parent / "models" / "qwen-vl-7b")
    QWEN_ENABLE: bool = True
    QWEN_QUANTIZE: str = "INT4"  # INT4 或 FP16
    QWEN_INFERENCE_TIMEOUT: int = 30  # 秒（远程访问需要更长超时）
    QWEN_OLLAMA_BASE_URL: str = "http://100.71.173.9:11434"  # Tailscale IP（远程 Ollama）
    QWEN_OLLAMA_MODEL: str = "qwen2.5:7b"  # 使用已安装的模型
    
    # YOLO 配置
    YOLO_MODEL_PATH: str = str(Path(__file__).parent.parent.parent.parent / "models" / "yolov8" / "best.pt")
    YOLO_CONF_THRESHOLD: float = 0.85
    YOLO_ENABLE: bool = True
    
    # OCR 配置
    PADDLE_OCR_ENABLE: bool = True
    PADDLE_OCR_CONF_THRESHOLD: float = 0.5
    
    # 降级策略配置
    FALLBACK_ENABLE: bool = True
    UI_AUTOMATOR_ENABLE: bool = True
    AIRTEST_ENABLE: bool = True
    
    # 执行配置
    ACTION_TIMEOUT: int = 30  # 秒
    SCREENSHOT_INTERVAL: int = 1  # 秒
    
    # 监控配置
    PERFORMANCE_SAMPLE_INTERVAL: int = 1  # 秒
    FPS_LOW_THRESHOLD: int = 15  # 帧
    CPU_HIGH_THRESHOLD: int = 90  # %
    MEM_HIGH_THRESHOLD: int = 85  # %
    TEMP_HIGH_THRESHOLD: int = 70  # 摄氏度
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = str(Path(__file__).parent.parent.parent.parent / "logs")
    LOG_RETENTION_DAYS: int = 7
    
    # 视频录制配置
    VIDEO_RING_BUFFER_SECONDS: int = 60
    VIDEO_FPS: int = 30
    VIDEO_KEYFRAME_INTERVAL: int = 2  # 秒
    SCRCPY_ENABLE: bool = True
    
    # 报告配置
    REPORT_DIR: str = str(Path(__file__).parent.parent.parent.parent / "reports")
    REPORT_RETENTION_DAYS: int = 30
    
    # JWT 配置
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 角色权限
    ROLES: List[str] = ["admin", "engineer", "observer"]
    
    class Config:
        env_file = str(Path(__file__).parent.parent.parent.parent / ".env")
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()

# 确保必要目录存在
for dir_path in [settings.DATABASE_PATH, settings.LOG_DIR, settings.REPORT_DIR]:
    Path(dir_path).parent.mkdir(parents=True, exist_ok=True)
