"""
日志监控层 - 实时过滤 Logcat
捕获 FATAL/ANR/OutOfMemoryError/Tombstone 等关键词
异常触发时自动保存最近 500 行日志
优化：Windows 编码处理 + Android 版本兼容
"""
import asyncio
import logging
import os
import locale
import re
from typing import Dict, List, Optional
from datetime import datetime
from app.core.database import execute_query
from app.devices.manager import DeviceManager

logger = logging.getLogger(__name__)


class LogMonitor:
    """日志监控器（优化：编码处理 + Android 版本兼容）"""
    
    # 需要监控的关键词
    CRITICAL_KEYWORDS = [
        "FATAL", "ANR", "OutOfMemoryError", "Tombstone",
        "SIGSEGV", "SIGABRT", "Assertion", "Crash", "DeadSystemException"
    ]
    
    # 堆栈指纹库（简化版，实际应从数据库加载）
    STACK_FINGERPRINTS = [
        "java.lang.NullPointerException",
        "java.lang.OutOfMemoryError",
        "android.app.RemoteServiceException",
        "android.os.DeadObjectException"
    ]
    
    def __init__(self, device_manager: DeviceManager):
        self.device_manager = device_manager
        self.running = False
        self.log_cache = {}  # device_id -> 最近日志缓存
        self.max_cache_size = 500  # 保存最近 500 行
        self.monitor_tasks = {}  # device_id -> task
        self.system_encoding = locale.getpreferredencoding()
        
    async def start_monitoring(self):
        """启动所有设备的日志监控"""
        self.running = True
        logger.info("📋 日志监控已启动")
        
        for device_id in self.device_manager.devices.keys():
            self.log_cache[device_id] = []
            task = asyncio.create_task(self.monitor_device_logs(device_id))
            self.monitor_tasks[device_id] = task
        
        # 等待所有任务
        if self.monitor_tasks:
            await asyncio.gather(*self.monitor_tasks.values(), return_exceptions=True)
    
    async def stop_monitoring(self):
        """停止监控"""
        self.running = False
        for task in self.monitor_tasks.values():
            task.cancel()
        logger.info("📋 日志监控已停止")
    
    async def monitor_device_logs(self, device_id: str):
        """
        监控单台设备的日志（优化：编码处理）
        
        使用 `logcat -v time` 持续读取日志流
        正确处理 Windows 下的编码问题
        """
        logger.info(f"开始监控设备 {device_id} 的日志")
        
        while self.running:
            try:
                device = self.device_manager.devices.get(device_id)
                if not device or device.status != "online":
                    await asyncio.sleep(2)
                    continue
                
                # 清除旧日志缓冲区
                await self.device_manager.run_adb_command(device_id, "shell logcat -c")
                
                # 启动 logcat
                # 设置环境变量（Windows 下强制 UTF-8）
                env = os.environ.copy()
                if os.name == 'nt':
                    env['PYTHONIOENCODING'] = 'utf-8'
                    env['PYTHONLEGACYWINDOWSSTDIO'] = 'utf-8'
                
                # 根据 Android 版本调整 logcat 参数
                sdk_version = device.sdk_version
                logcat_cmd = self._get_logcat_command(sdk_version)
                
                proc = await asyncio.create_subprocess_shell(
                    f"adb -s {device_id} {logcat_cmd}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env
                )
                
                # 读取日志
                while self.running and proc.returncode is None:
                    try:
                        line = await asyncio.wait_for(
                            proc.stdout.readline(),
                            timeout=1.0
                        )
                    except asyncio.TimeoutError:
                        continue
                    
                    if not line:
                        break
                    
                    # 解码日志行（处理编码问题）
                    log_line = self._decode_line(line)
                    
                    # 清洗日志行（移除控制字符）
                    log_line = self._clean_log_line(log_line)
                    
                    # 添加到缓存
                    self.add_to_cache(device_id, log_line)
                    
                    # 检查是否为异常日志
                    if self.is_critical_log(log_line):
                        logger.warning(f"🔴 设备 {device_id} 发现异常日志: {log_line[:100]}")
                        await self.handle_critical_log(device_id, log_line)
                
                # 进程结束，清理
                try:
                    proc.kill()
                except:
                    pass
                await proc.wait()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"监控设备 {device_id} 日志时出错: {e}")
                await asyncio.sleep(5)  # 等待后重试
    
    def _get_logcat_command(self, sdk_version: int) -> str:
        """
        根据 Android 版本获取 logcat 命令
        
        Android 4.x: 使用 `logcat -v time`（基本格式）
        Android 5+: 使用 `logcat -v time -b main`（指定缓冲区）
        Android 8+: 支持 `logcat -v time --format=threadtime`
        """
        if sdk_version >= 26:  # Android 8.0+
            return "logcat -v threadtime"
        elif sdk_version >= 21:  # Android 5.0+
            return "logcat -v time -b main"
        else:  # Android 4.x
            return "logcat -v time"
    
    def _decode_line(self, line: bytes) -> str:
        """
        解码日志行（处理编码问题）
        
        尝试多种编码，直到成功解码
        
        Args:
            line: 原始字节流
            
        Returns:
            解码后的字符串
        """
        # 尝试使用 UTF-8 解码
        try:
            return line.decode('utf-8')
        except UnicodeDecodeError:
            pass
        
        # 尝试使用系统编码解码
        try:
            return line.decode(self.system_encoding)
        except UnicodeDecodeError:
            pass
        
        # 尝试使用 GBK 解码（Windows 中文系统）
        try:
            return line.decode('gbk')
        except UnicodeDecodeError:
            pass
        
        # 最后手段：使用 UTF-8 并忽略错误
        return line.decode('utf-8', errors='ignore')
    
    def _clean_log_line(self, log_line: str) -> str:
        """
        清洗日志行（移除控制字符和 ANSI 转义序列）
        
        Args:
            log_line: 原始日志行
            
        Returns:
            清洗后的日志行
        """
        try:
            import re
            
            # 移除 ANSI 转义序列
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            log_line = ansi_escape.sub('', log_line)
            
            # 移除其他控制字符（保留换行符和制表符）
            log_line = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', log_line)
            
            return log_line
        except Exception as e:
            logger.error(f"清洗日志行失败: {e}")
            return log_line
    
    def add_to_cache(self, device_id: str, log_line: str):
        """添加日志到缓存（环形缓冲）"""
        cache = self.log_cache.get(device_id, [])
        cache.append({
            "timestamp": datetime.now().isoformat(),
            "content": log_line
        })
        
        # 保持缓存大小
        if len(cache) > self.max_cache_size:
            cache = cache[-self.max_cache_size:]
        
        self.log_cache[device_id] = cache
    
    def is_critical_log(self, log_line: str) -> bool:
        """
        判断是否为关键日志
        
        使用堆栈指纹匹配（SimHash 简化版）
        """
        # 简单关键词匹配
        for keyword in self.CRITICAL_KEYWORDS:
            if keyword in log_line:
                return True
        
        # 堆栈指纹匹配（简化版）
        for fingerprint in self.STACK_FINGERPRINTS:
            if fingerprint in log_line:
                return True
        
        return False
    
    async def handle_critical_log(self, device_id: str, log_line: str):
        """处理关键日志"""
        try:
            # 获取当前执行 ID
            from app.core.database import fetch_one
            device_row = await fetch_one(
                "SELECT id FROM devices WHERE device_id = ?",
                (device_id,)
            )
            
            if device_row:
                device_db_id = device_row["id"]
                execution_row = await fetch_one("""
                    SELECT id FROM executions 
                    WHERE device_id = ? AND status = 'running'
                    ORDER BY start_time DESC LIMIT 1
                """, (device_db_id,))
                
                execution_id = execution_row["id"] if execution_row else None
                
                # 保存到数据库
                await execute_query("""
                    INSERT INTO logs (execution_id, device_id, level, tag, message)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    execution_id,
                    device_db_id,
                    "FATAL" if "FATAL" in log_line else "ERROR",
                    self.extract_tag(log_line),
                    log_line[:500]  # 限制长度
                ))
                
                # 触发异常保存（视频、截图）
                await self.trigger_exception_save(device_id, execution_id)
                
        except Exception as e:
            logger.error(f"处理关键日志失败: {e}")
    
    def extract_tag(self, log_line: str) -> str:
        """从日志行提取 tag"""
        match = re.search(r'\s(\w+)\s*:', log_line)
        return match.group(1) if match else "Unknown"
    
    async def trigger_exception_save(self, device_id: str, execution_id: Optional[int]):
        """触发异常保存（视频、截图）"""
        try:
            logger.info(f"💾 触发异常保存: 设备 {device_id}")
            
            # 保存当前截图
            screenshot_path = await self.device_manager.take_screenshot(device_id)
            
            # 保存日志到报告
            if execution_id:
                recent_logs = self.get_recent_logs(device_id, 500)
                log_text = "\n".join([log["content"] for log in recent_logs])
                
                await execute_query("""
                    UPDATE executions 
                    SET screenshot_path = ?, error_message = ?
                    WHERE id = ?
                """, (screenshot_path, log_text[:1000], execution_id))
            
            # 通知视频录制模块保存环形缓冲
            from app.monitor.video_recorder import VideoRecorder
            video_recorder = VideoRecorder.get_instance()
            if video_recorder:
                await video_recorder.save_buffer(device_id, execution_id)
                
        except Exception as e:
            logger.error(f"触发异常保存失败: {e}")
    
    def get_recent_logs(self, device_id: str, count: int = 500) -> List[Dict]:
        """获取最近的日志"""
        cache = self.log_cache.get(device_id, [])
        return cache[-count:] if cache else []
    
    async def get_logs_for_execution(self, execution_id: int) -> List[Dict]:
        """获取指定执行的日志"""
        from app.core.database import fetch_all
        rows = await fetch_all(
            "SELECT * FROM logs WHERE execution_id = ? ORDER BY timestamp",
            (execution_id,)
        )
        return [dict(row) for row in rows]
    
    async def get_logs_for_device(self, device_id: str, count: int = 100) -> List[str]:
        """获取指定设备的最近日志（供 AI 分析）"""
        cache = self.log_cache.get(device_id, [])
        logs = [log["content"] for log in cache[-count:]]
        return logs
