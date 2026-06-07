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
from app.stream.screen_stream import screen_streamer

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
    
    # 设置屏幕流推送器的 ADB 路径
    screen_streamer.set_adb_path(settings.ADB_PATH)
    logger.info("✅ 屏幕流推送器就绪")
    
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

# 截图文件静态访问（先于 SPA catch-all 注册）
screenshots_dir = Path(__file__).parent.parent / "logs" / "screenshots"
if screenshots_dir.exists():
    app.mount("/api/v1/files", StaticFiles(directory=str(screenshots_dir)), name="screenshots")
    logger.info(f"✅ 截图文件服务已启动：{screenshots_dir}")
else:
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/api/v1/files", StaticFiles(directory=str(screenshots_dir)), name="screenshots")
    logger.info(f"✅ 截图目录已创建并启动服务：{screenshots_dir}")


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


@app.websocket("/ws/device/{device_id}/screen")
async def websocket_device_screen(websocket: WebSocket, device_id: str):
    """
    设备屏幕实时流 WebSocket
    
    连接后后端自动启动 capture loop，持续通过 ADB exec-out 获取 PNG 帧，
    以二进制消息推送到前端。前端用 createImageBitmap + canvas 渲染。
    客户端断开后 capture loop 自动停止。
    """
    await websocket.accept()
    client_id = await screen_streamer.register(device_id, websocket)
    logger.info(f"📺 设备 {device_id} 屏幕流客户端 #{client_id} 已连接")
    
    try:
        # 保持连接，接收心跳/断开通知
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if msg == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # 30秒无消息，发个ping探测
                try:
                    await websocket.send_text("ping")
                except Exception:
                    break
    except (WebSocketDisconnect, Exception) as e:
        logger.info(f"📺 设备 {device_id} 屏幕流客户端 #{client_id} 断开: {e}")
    finally:
        await screen_streamer.unregister(device_id, client_id)


# ============ 静态文件挂载（必须在所有路由之后）============
# Starlette 中 Mount 按 prefix 匹配，"/" 会捕获所有路径，
# 必须在所有 @app.get/@app.websocket 路由之后注册，否则会拦截 WebSocket 请求

# 静态文件服务（前端构建产物，SPA catch-all）
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(html=True, directory=str(frontend_dist)), name="frontend")
    logger.info(f"✅ 前端静态文件服务已启动：{frontend_dist}")
else:
    logger.warning(f"⚠️ 前端构建目录不存在：{frontend_dist}，将只提供 API 服务")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
