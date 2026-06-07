"""测试配置加载"""
import sys
from pathlib import Path

# 添加 backend 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings

print(f"ADB_PATH = {settings.ADB_PATH!r}")
print(f"DATABASE_PATH = {settings.DATABASE_PATH!r}")
print(f"OLLAMA_BASE_URL = {settings.QWEN_OLLAMA_BASE_URL!r}")
