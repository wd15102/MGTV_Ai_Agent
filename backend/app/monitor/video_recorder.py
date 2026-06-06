"""
视频录制层 - 环形缓冲
使用 scrcpy 低延迟投屏 + FFmpeg 录制
内存中保留最近 60 秒，异常时写入磁盘
"""
import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import aiofiles

logger = logging.getLogger(__name__)


class VideoRecorder:
    """视频录制器（单例模式）"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.ring_buffer_seconds = 60  # 环形缓冲秒数
        self.fps = 30
        self.keyframe_interval = 2  # 秒
        self.running = False
        self.devices = {}  # device_id -> process info
        self.video_dir = Path("reports/videos")
        self.video_dir.mkdir(parents=True, exist_ok=True)
        
    @classmethod
    def get_instance(cls):
        """获取单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def start_recording(self, device_id: str):
        """开始录制（环形缓冲）"""
        if device_id in self.devices:
            logger.warning(f"设备 {device_id} 已在录制中")
            return
        
        try:
            # 使用 scrcpy 获取屏幕流，管道传递给 FFmpeg
            scrcpy_cmd = f"scrcpy -s {device_id} --no-display --record=-"
            ffmpeg_cmd = (
                f"ffmpeg -i - -c:v libx264 -preset ultrafast "
                f"-f segment -segment_time {self.ring_buffer_seconds} "
                f"-segment_wrap 2 -y {self.video_dir}/{device_id}_%03d.mp4"
            )
            
            # 启动 FFmpeg 进程
            proc = await asyncio.create_subprocess_shell(
                ffmpeg_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )
            
            self.devices[device_id] = {
                "process": proc,
                "start_time": datetime.now(),
                "saved_videos": []
            }
            
            logger.info(f"🎥 设备 {device_id} 开始录制")
            
            # 启动日志读取任务
            asyncio.create_task(self._read_stderr(device_id, proc))
            
        except Exception as e:
            logger.error(f"启动录制失败: {e}")
    
    async def _read_stderr(self, device_id: str, proc: asyncio.subprocess.Process):
        """读取 FFmpeg 错误输出"""
        try:
            while True:
                line = await proc.stderr.readline()
                if not line:
                    break
                # 可在此处解析 FFmpeg 输出
        except Exception as e:
            logger.error(f"读取 FFmpeg 输出失败: {e}")
    
    async def save_buffer(self, device_id: str, execution_id: Optional[int] = None):
        """保存环形缓冲（异常触发）"""
        if device_id not in self.devices:
            logger.warning(f"设备 {device_id} 未录制")
            return
        
        try:
            info = self.devices[device_id]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.video_dir / f"{device_id}_{timestamp}_exception.mp4"
            
            # 发送信号给 FFmpeg 保存当前缓冲
            proc = info["process"]
            if proc.returncode is None:
                proc.send_signal(subprocess.signal.SIGUSR1)  # 触发分段
                await asyncio.sleep(1)  # 等待写入
            
            # 复制最近的视频段
            import shutil
            recent_files = sorted(self.video_dir.glob(f"{device_id}_*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True)
            
            if recent_files:
                saved_path = self.video_dir / f"{device_id}_{timestamp}_exception.mp4"
                shutil.copy(recent_files[0], saved_path)
                
                # 更新数据库
                if execution_id:
                    from app.core.database import execute_query
                    await execute_query(
                        "UPDATE executions SET video_path = ? WHERE id = ?",
                        (str(saved_path), execution_id)
                    )
                
                logger.info(f"💾 异常视频已保存: {saved_path}")
                info["saved_videos"].append(str(saved_path))
            
        except Exception as e:
            logger.error(f"保存环形缓冲失败: {e}")
    
    async def stop_recording(self, device_id: str):
        """停止录制"""
        if device_id not in self.devices:
            return
        
        try:
            info = self.devices[device_id]
            proc = info["process"]
            
            # 发送终止信号
            proc.terminate()
            await proc.wait()
            
            del self.devices[device_id]
            logger.info(f"🎥 设备 {device_id} 停止录制")
            
        except Exception as e:
            logger.error(f"停止录制失败: {e}")
    
    async def stop_all(self):
        """停止所有录制"""
        for device_id in list(self.devices.keys()):
            await self.stop_recording(device_id)
    
    def is_recording(self, device_id: str) -> bool:
        """检查是否正在录制"""
        return device_id in self.devices
