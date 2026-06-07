"""
屏幕流推送器 - 实时 ADB 画面推送（非轮询）
 
核心模式：后端持续通过 ADB exec-out 获取 PNG 帧，通过 WebSocket 二进制帧推送到前端。
不依赖任何第三方投屏工具，纯 ADB 原生命令。
 
工作原理：
  1. 为每台设备维护一个 asyncio capture loop
  2. 循环执行 adb exec-out shell "screencap -p" 获取原始 PNG 字节
  3. 通过 WebSocket broadcast 推送到所有连接的客户端
  4. 客户端用 createImageBitmap 高效解码并在 canvas 上渲染
 
局限：
  - 依赖 ADB 带宽：USB 连接可达 20-30fps，WiFi 约 8-15fps
  - 不可用于投屏操作（仅在后台截屏推送）
"""
import asyncio
import logging
from typing import Dict, List, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ScreenStreamer:
    """屏幕流推送器（单例）"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # {device_id: {client_id: WebSocket}}
        self.clients: Dict[str, Dict[int, WebSocket]] = {}
        self._client_counter = 0
        # 每设备的 capture loop 是否在运行
        self._running: Dict[str, bool] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._adb_path = "adb"
    
    def set_adb_path(self, path: str):
        self._adb_path = path
    
    def _get_or_create_clients(self, device_id: str) -> Dict[int, WebSocket]:
        if device_id not in self.clients:
            self.clients[device_id] = {}
        return self.clients[device_id]
    
    async def register(self, device_id: str, ws: WebSocket) -> int:
        """注册一个 WebSocket 客户端，返回 client_id"""
        self._client_counter += 1
        cid = self._client_counter
        clients = self._get_or_create_clients(device_id)
        clients[cid] = ws
        logger.info(f"[ScreenStream] 设备 {device_id} 注册客户端 #{cid}，当前连接数: {len(clients)}")
        
        # 如果该设备的 capture loop 未启动，启动它
        if device_id not in self._tasks or self._tasks[device_id].done():
            self._running[device_id] = True
            self._tasks[device_id] = asyncio.create_task(self._capture_loop(device_id))
            logger.info(f"[ScreenStream] 设备 {device_id} capture loop 已启动")
        
        return cid
    
    async def unregister(self, device_id: str, client_id: int):
        """注销一个 WebSocket 客户端"""
        clients = self.clients.get(device_id, {})
        if client_id in clients:
            del clients[client_id]
        
        remaining = len(clients)
        logger.info(f"[ScreenStream] 设备 {device_id} 移除客户端 #{client_id}，剩余连接: {remaining}")
        
        # 如果该设备没有客户端了，停止 capture loop
        if remaining == 0:
            self._running[device_id] = False
            if device_id in self._tasks and not self._tasks[device_id].done():
                self._tasks[device_id].cancel()
                logger.info(f"[ScreenStream] 设备 {device_id} capture loop 已停止")
            # 清理空记录
            self.clients.pop(device_id, None)
    
    async def broadcast(self, device_id: str, frame_data: bytes):
        """广播一帧到所有连接的客户端"""
        clients = self.clients.get(device_id, {})
        if not clients:
            return
        
        dead_clients = []
        for cid, ws in clients.items():
            try:
                await ws.send_bytes(frame_data)
            except Exception:
                dead_clients.append(cid)
        
        # 清理断开的客户端
        for cid in dead_clients:
            clients.pop(cid, None)
            logger.debug(f"[ScreenStream] 清理断开的客户端 #{cid}")
    
    async def _capture_loop(self, device_id: str):
        """
        持续截屏循环
        使用 adb exec-out shell "screencap -p" 获取原始 PNG 字节流
        adb exec-out vs adb shell: exec-out 绕过 shell 的管道处理，
        直接输出原始二进制，避免 \r\n 污染
        """
        logger.info(f"[ScreenStream] 设备 {device_id} capture loop 开始运行")
        
        while self._running.get(device_id, False):
            frame_data = await self._capture_frame(device_id)
            if frame_data:
                await self.broadcast(device_id, frame_data)
            else:
                # 截屏失败，等待后重试
                await asyncio.sleep(0.1)
        
        logger.info(f"[ScreenStream] 设备 {device_id} capture loop 已退出")
    
    async def _capture_frame(self, device_id: str) -> Optional[bytes]:
        """
        执行一次 ADB 截屏，返回 PNG 字节数据
        使用 exec-out 直接获取原始二进制输出
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                self._adb_path, "-s", device_id,
                "exec-out", "shell", "screencap", "-p",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            
            try:
                data, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                logger.warning(f"[ScreenStream] 设备 {device_id} 截屏超时")
                return None
            
            if not data or len(data) < 100:
                return None
            
            # 验证是否是有效的 PNG
            if data[:4] != b'\x89PNG':
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"[ScreenStream] 设备 {device_id} 截屏异常: {e}")
            return None
    
    def is_streaming(self, device_id: str) -> bool:
        """检查某设备是否正在推流"""
        return self._running.get(device_id, False) and self.clients.get(device_id, {})


# 全局单例
screen_streamer = ScreenStreamer()
