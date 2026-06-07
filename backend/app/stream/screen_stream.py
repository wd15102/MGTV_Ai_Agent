"""
屏幕流推送器 v3 - H.264 硬件编码实时流（scrcpy） + PNG 兜底

核心策略：
1. **主要方案：scrcpy H.264 流** — 通过 ADB forward + scrcpy-server 获取 H.264 帧，
   硬件编码解码为 JPEG，推送到 WebSocket。目标 15-30 FPS。
2. **兜底方案：PNG screencap 流** — 持久 ADB shell 循环，通过 wm size 降分辨率
   减少数据量（~100KB/帧, ~1.2 FPS）。

自动选择：先尝试 scrcpy H.264，若失败（如设备不兼容）自动回退 PNG。
"""

import asyncio
import logging
import os
from typing import Dict, Optional

from fastapi import WebSocket

from app.stream.scrcpy_reader import (
    ScrcpyDeviceStreamReader,
    find_scrcpy_server,
)

logger = logging.getLogger(__name__)


class ScreenStreamer:
    """屏幕流推送器（单例）- 使用 scrcpy H.264 流"""
    
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
        
        self.clients: Dict[str, Dict[int, WebSocket]] = {}
        self._client_counter = 0
        self._running: Dict[str, bool] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        
        # ADB 配置
        self._adb_path = "adb"
        
        # 流读取器
        self._readers: Dict[str, ScrcpyDeviceStreamReader] = {}
    
    def set_adb_path(self, path: str):
        self._adb_path = path or "adb"
    
    def get_scrcpy_server_path(self) -> Optional[str]:
        """获取 scrcpy-server 路径"""
        return os.environ.get("SCRCPY_SERVER_PATH") or find_scrcpy_server()
    
    async def register(self, device_id: str, ws: WebSocket) -> int:
        """注册 WebSocket 客户端"""
        self._client_counter += 1
        cid = self._client_counter
        clients = self._get_clients(device_id)
        clients[cid] = ws
        count = len(clients)
        logger.info(f"[ScreenStream] 设备 {device_id} 注册客户端 #{cid}，连接数: {count}")
        
        # 首次连接时启动截屏任务
        if device_id not in self._tasks or self._tasks[device_id].done():
            self._running[device_id] = True
            self._tasks[device_id] = asyncio.create_task(
                self._capture_loop(device_id)
            )
        
        return cid
    
    async def unregister(self, device_id: str, client_id: int):
        """注销 WebSocket 客户端"""
        clients = self.clients.get(device_id, {})
        clients.pop(client_id, None)
        remaining = len(clients)
        logger.info(f"[ScreenStream] 设备 {device_id} 客户端 #{client_id} 断开，剩余 {remaining}")
        
        if remaining == 0:
            await self._stop_device_stream(device_id)
    
    def _get_clients(self, device_id: str) -> Dict[int, WebSocket]:
        if device_id not in self.clients:
            self.clients[device_id] = {}
        return self.clients[device_id]
    
    async def _stop_device_stream(self, device_id: str):
        """停止设备流"""
        self._running[device_id] = False
        
        if device_id in self._tasks and not self._tasks[device_id].done():
            self._tasks[device_id].cancel()
        self._tasks.pop(device_id, None)
        self.clients.pop(device_id, None)
        
        reader = self._readers.pop(device_id, None)
        if reader:
            await reader.stop()
            logger.info(f"[ScreenStream] 设备 {device_id} scrcpy 读取器已停止")
    
    async def broadcast(self, device_id: str, frame_data: bytes):
        """广播一帧到所有 WebSocket 客户端"""
        clients = self.clients.get(device_id, {})
        if not clients:
            return
        
        dead = []
        for cid, ws in clients.items():
            try:
                await ws.send_bytes(frame_data)
            except Exception as e:
                logger.debug(f"[ScreenStream] 客户端 #{cid} 发送失败: {e}")
                dead.append(cid)
        
        for cid in dead:
            clients.pop(cid, None)
    
    async def _capture_loop(self, device_id: str):
        """
        截屏循环：使用 scrcpy H.264 流
        
        流程：
        1. 创建 ScrcpyDeviceStreamReader
        2. 启动 H.264 流
        3. 循环 get_frame() -> broadcast()
        4. 停止后清理
        """
        logger.info(f"[ScreenStream] 设备 {device_id} 启动 H.264 capture loop")
        
        server_path = self.get_scrcpy_server_path()
        if not server_path:
            logger.warning(f"[ScreenStream] 未找到 scrcpy-server，使用 PNG 兜底方案")
            await self._png_fallback_loop(device_id)
            return
        
        reader = ScrcpyDeviceStreamReader(
            adb_path=self._adb_path,
            device_id=device_id,
            scrcpy_server_path=server_path,
            max_size=720,
            bit_rate=2000000,
            decode_every_n=2,  # 每 2 个 H.264 帧解码 1 帧 -> ~15 FPS 输出
        )
        self._readers[device_id] = reader
        
        if not await reader.start():
            logger.warning(f"[ScreenStream] scrcpy 启动失败，回退 PNG 方案")
            self._readers.pop(device_id, None)
            await self._png_fallback_loop(device_id)
            return
        
        stream_info = reader.stream_info
        logger.info(f"[ScreenStream] scrcpy H.264 流就绪: "
                    f"{stream_info['codec']} {stream_info['width']}x{stream_info['height']}")
        
        # 推送首帧通知
        clients = self._get_clients(device_id)
        for ws in clients.values():
            try:
                await ws.send_json({
                    "type": "stream_info",
                    "width": stream_info["width"],
                    "height": stream_info["height"],
                    "codec": stream_info["codec"],
                    "fps": "~15"
                })
            except Exception:
                pass
        
        no_frame_count = 0
        frame_count = 0
        
        while self._running.get(device_id, False):
            frame = await reader.get_frame(timeout=5.0)
            
            if frame:
                no_frame_count = 0
                frame_count += 1
                await self.broadcast(device_id, frame)
            else:
                no_frame_count += 1
                if no_frame_count > 6:  # 约 30 秒无帧
                    logger.warning(f"[ScreenStream] 设备 {device_id} 超过 30 秒无帧，重启流")
                    await reader.stop()
                    
                    # 重新创建并启动
                    reader = ScrcpyDeviceStreamReader(
                        adb_path=self._adb_path,
                        device_id=device_id,
                        scrcpy_server_path=server_path,
                        max_size=720,
                        bit_rate=2000000,
                        decode_every_n=2,
                    )
                    self._readers[device_id] = reader
                    
                    if not await reader.start():
                        logger.error(f"[ScreenStream] 重连 scrcpy 失败")
                        break
                    
                    no_frame_count = 0
                    logger.info(f"[ScreenStream] 设备 {device_id} scrcpy 流已重启")
        
        # 停止
        await reader.stop()
        self._readers.pop(device_id, None)
        logger.info(f"[ScreenStream] 设备 {device_id} capture loop 退出（共推送 {frame_count} 帧）")
    
    async def _png_fallback_loop(self, device_id: str):
        """
        PNG 兜底方案：持久 ADB shell screencap 循环
        
        当 scrcpy H.264 不可用时自动回退
        """
        logger.info(f"[ScreenStream] 设备 {device_id} 启动 PNG 兜底 capture loop")
        
        # 运行时导入避免循环依赖
        from app.stream.screen_stream_png import PngStreamReader
        
        reader = PngStreamReader(self._adb_path, device_id)
        self._readers.get(device_id)  # 保留兼容性
        
        if not await reader.start():
            logger.error(f"[ScreenStream] PNG 兜底也启动失败")
            return
        
        no_frame_count = 0
        frame_count = 0
        
        while self._running.get(device_id, False):
            frame = await reader.get_frame()
            
            if frame:
                no_frame_count = 0
                frame_count += 1
                await self.broadcast(device_id, frame)
            else:
                no_frame_count += 1
                if no_frame_count > 5:  # ~40 秒无帧
                    logger.warning(f"[ScreenStream] PNG 兜底 {device_id} 无帧，重启")
                    await reader.stop()
                    reader = PngStreamReader(self._adb_path, device_id)
                    if not await reader.start():
                        break
                    no_frame_count = 0
        
        await reader.stop()
        logger.info(f"[ScreenStream] PNG 兜底 {device_id} 退出（共推送 {frame_count} 帧）")


# 全局单例
screen_streamer = ScreenStreamer()