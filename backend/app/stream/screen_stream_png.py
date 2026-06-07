"""
PNG 兜底屏幕流方案 - 持久 ADB shell screencap 循环

当 scrcpy H.264 方案不可用时自动回退到此方案。
性能：720p 下 ~100KB/帧，~1.2 FPS（WiFi ADB）。
"""

import asyncio
import logging
import os
import re
import subprocess
import threading
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

PNG_HEADER = b'\x89PNG'
IEND_MARKER = b'\x00\x00\x00\x00IEND\xae\x42\x60\x82'
FRAME_READ_TIMEOUT = 8.0


class PngStreamReader:
    """持久 ADB shell 流读取器（PNG 兜底方案）"""
    
    STREAM_RESOLUTION = "720x405"
    
    def __init__(self, adb_path: str, device_id: str):
        self._adb_path = adb_path
        self._device_id = device_id
        self._process: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        
        self._lock = threading.Lock()
        self._latest_frame: Optional[bytes] = None
        self._frame_event = threading.Event()
        self._original_resolution: Optional[str] = None
    
    async def start(self) -> bool:
        """启动持久 ADB shell 进程，设置虚拟分辨率"""
        if self._process and self._process.poll() is None:
            return True
        
        # 记录原始分辨率
        self._original_resolution = self._get_resolution()
        if self._original_resolution:
            logger.info(f"[PngStream] 原始分辨率: {self._original_resolution.strip()}")
        
        # 设置低分辨率
        self._set_resolution(self.STREAM_RESOLUTION)
        
        args = [
            self._adb_path, "-s", self._device_id, "shell",
            "while true; do screencap -p; done"
        ]
        logger.info(f"[PngStream] 设备 {self._device_id} 启动持久 ADB shell")
        
        try:
            self._process = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0
            )
        except FileNotFoundError:
            logger.error(f"[PngStream] ADB 未找到: {self._adb_path}")
            self._reset_resolution()
            return False
        except Exception as e:
            logger.error(f"[PngStream] 启动失败: {e}")
            self._reset_resolution()
            return False
        
        if not self._process.stdout:
            self._reset_resolution()
            return False
        
        self._running = True
        self._thread = threading.Thread(
            target=self._read_loop, daemon=True,
            name=f"png-stream-{self._device_id.replace(':', '_')}"
        )
        self._thread.start()
        return True
    
    def _get_resolution(self) -> Optional[str]:
        try:
            r = subprocess.run(
                [self._adb_path, "-s", self._device_id, "shell", "wm size"],
                capture_output=True, timeout=5, text=True
            )
            return r.stdout.strip()
        except Exception as e:
            logger.warning(f"[PngStream] 获取分辨率失败: {e}")
            return None
    
    def _set_resolution(self, size: str):
        subprocess.run(
            [self._adb_path, "-s", self._device_id, "shell", f"wm size {size}"],
            capture_output=True, timeout=5
        )
    
    def _reset_resolution(self):
        if self._original_resolution:
            m = re.search(r'Physical size:?\s*(\d+x\d+)', self._original_resolution)
            if m:
                orig = m.group(1)
                if orig != self.STREAM_RESOLUTION:
                    self._set_resolution(orig)
                    logger.info(f"[PngStream] 恢复原始分辨率: {orig}")
    
    def _read_loop(self):
        """后台线程：持续读取 stdout，检测 IEND 边界提取 PNG 帧"""
        buf = bytearray()
        while self._running and self._process and self._process.stdout:
            try:
                chunk = self._process.stdout.read(65536)
                if not chunk:
                    break
                buf.extend(chunk)
                
                while True:
                    iend_pos = buf.find(IEND_MARKER)
                    if iend_pos == -1:
                        break
                    
                    frame_end = iend_pos + len(IEND_MARKER)
                    png_start = buf.find(PNG_HEADER, max(0, iend_pos - 2048))
                    if png_start >= 0:
                        frame = bytes(buf[png_start:frame_end])
                        if len(frame) > 500 and frame[-4:] == b'IEND':
                            self._notify_frame(frame)
                    
                    buf = buf[frame_end:]
                
                if len(buf) > 10 * 1024 * 1024:
                    buf = buf[-1048576:]
            except Exception as e:
                logger.error(f"[PngStream] 读取异常: {e}", exc_info=True)
                break
        self._running = False
    
    def _notify_frame(self, frame_data: bytes):
        with self._lock:
            self._latest_frame = frame_data
        self._frame_event.set()
    
    async def get_frame(self) -> Optional[bytes]:
        with self._lock:
            if self._latest_frame is not None:
                frame = self._latest_frame
                self._latest_frame = None
                return frame
        
        loop = asyncio.get_running_loop()
        def _wait():
            self._frame_event.wait(FRAME_READ_TIMEOUT)
            self._frame_event.clear()
        await loop.run_in_executor(None, _wait)
        
        with self._lock:
            frame = self._latest_frame
            self._latest_frame = None
            return frame
    
    async def stop(self):
        self._running = False
        if self._process:
            try:
                self._process.kill()
                self._process.wait(timeout=3)
            except Exception:
                pass
            self._process = None
        self._thread = None
        self._reset_resolution()
