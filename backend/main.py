"""
AI智能测试大屏平台 - 后端主入口
基于 FastAPI + Uvicorn
支持 ≤2 台设备的 AI 驱动自动化测试
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.api.router import router as api_router
from app.core.config import settings
from app.core.database import init_db, close_db
from app.devices.manager import DeviceManager
from app.monitor.performance import PerformanceMonitor
from app.ai.agent import AIAgent

# 配置日志（修复：使用绝对路径，自动创建 logs 目录）
import os
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'platform.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 全局对象
device_manager: DeviceManager = None
performance_monitor: PerformanceMonitor = None
ai_agent: AIAgent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global device_manager, performance_monitor, ai_agent
    
    logger.info("🚀 AI智能测试大屏平台启动中...")
    
    # 初始化数据库
    await init_db()
    logger.info("✅ 数据库初始化完成")
    
    # 初始化设备管理器和AI Agent
    device_manager = DeviceManager()
    ai_agent = AIAgent()
    performance_monitor = PerformanceMonitor(device_manager)
    
    # 启动设备心跳检测
    asyncio.create_task(device_manager.start_heartbeat())
    logger.info("✅ 设备管理器启动完成")
    
    # 启动性能监控
    asyncio.create_task(performance_monitor.start_monitoring())
    logger.info("✅ 性能监控启动完成")
    
    logger.info("🎉 平台启动完成！")
    
    yield
    
    # 清理资源
    logger.info("🛑 平台关闭中...")
    await close_db()
    if device_manager:
        await device_manager.cleanup()
    logger.info("✅ 平台已安全关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="AI智能测试大屏平台",
    description="基于AI视觉理解的智能自动化测试平台",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix="/api/v1")

# 静态文件服务（前端构建产物）
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(html=True), name="frontend")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "AI智能测试大屏平台",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "devices": len(device_manager.devices) if device_manager else 0,
        "timestamp": asyncio.get_event_loop().time()
    }


@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """Dashboard 实时数据 WebSocket"""
    await websocket.accept()
    try:
        while True:
            # 发送实时数据
            data = {
                "devices": await device_manager.get_status() if device_manager else [],
                "performance": await performance_monitor.get_latest() if performance_monitor else {},
                "ai_status": ai_agent.get_status() if ai_agent else {}
            }
            await websocket.send_json(data)
            await asyncio.sleep(1)  # 每秒推送一次
    except WebSocketDisconnect:
        logger.info("Dashboard WebSocket 断开连接")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
