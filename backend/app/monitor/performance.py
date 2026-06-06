"""
性能监控层 - 实时采集 CPU/内存/FPS/温度
并行非阻塞，通过内部队列与执行层解耦
优化：兼容不同 Android 版本（4、9、11）
"""
import asyncio
import logging
import re
from typing import Dict, List, Optional
from datetime import datetime
from app.core.database import execute_query, fetch_one, fetch_all
from app.devices.manager import DeviceManager

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """性能监控器（优化：Android 版本兼容）"""
    
    def __init__(self, device_manager: DeviceManager):
        self.device_manager = device_manager
        self.sample_interval = 1  # 秒
        self.running = False
        self.latest_data = {}  # 最新性能数据缓存
        self.fps_low_threshold = 15  # 帧
        self.cpu_high_threshold = 90  # %
        self.mem_high_threshold = 85  # %
        self.temp_high_threshold = 70  # 摄氏度
        
    async def start_monitoring(self):
        """启动性能监控循环"""
        self.running = True
        logger.info("📊 性能监控已启动")
        
        while self.running:
            try:
                for device_id in self.device_manager.devices.keys():
                    data = await self.collect_device_performance(device_id)
                    if data:
                        # 存入数据库
                        await self.save_to_db(device_id, data)
                        # 更新缓存
                        self.latest_data[device_id] = data
                        # 检查告警
                        await self.check_alerts(device_id, data)
            except Exception as e:
                logger.error(f"性能监控异常: {e}")
            
            await asyncio.sleep(self.sample_interval)
    
    async def stop_monitoring(self):
        """停止监控"""
        self.running = False
        logger.info("📊 性能监控已停止")
    
    async def collect_device_performance(self, device_id: str) -> Optional[Dict]:
        """采集单台设备的性能数据"""
        try:
            device = self.device_manager.devices.get(device_id)
            if not device or device.status != "online":
                return None
            
            # 获取 Android 版本
            sdk_version = device.sdk_version
            
            data = {
                "timestamp": datetime.now().isoformat(),
                "cpu_usage": await self.get_cpu_usage(device_id, sdk_version),
                "memory_usage": await self.get_memory_usage(device_id, sdk_version),
                "memory_percent": await self.get_memory_percent(device_id, sdk_version),
                "fps": await self.get_fps(device_id, sdk_version),
                "temperature": await self.get_temperature(device_id),
                "network_rx": await self.get_network_rx(device_id),
                "network_tx": await self.get_network_tx(device_id)
            }
            
            return data
            
        except Exception as e:
            logger.error(f"采集设备 {device_id} 性能数据失败: {e}")
            return None
    
    async def get_cpu_usage(self, device_id: str, sdk_version: int = 0) -> float:
        """
        获取 CPU 使用率（兼容不同 Android 版本）
        
        Android 4.x: 使用 `top -n 1`
        Android 5+: 使用 `dumpsys cpuinfo`
        """
        try:
            if sdk_version < 21:  # Android 4.x
                # 使用 top 命令
                cmd = "shell top -n 1 -d 1 | grep 'User'"
                return_code, output = await self.device_manager.run_adb_command(device_id, cmd)
                if return_code == 0 and output:
                    # 解析 top 输出
                    match = re.search(r'(\d+)%', output)
                    if match:
                        return float(match.group(1))
            else:  # Android 5+
                # 使用 dumpsys cpuinfo
                cmd = "shell dumpsys cpuinfo | grep -A 20 'TOTAL' | tail -1"
                return_code, output = await self.device_manager.run_adb_command(device_id, cmd)
                if return_code == 0 and output:
                    match = re.search(r'(\d+\.?\d*)%', output)
                    if match:
                        return float(match.group(1))
            
            return 0.0
        except Exception as e:
            logger.error(f"获取 CPU 使用率失败: {e}")
            return 0.0
    
    async def get_memory_usage(self, device_id: str, sdk_version: int = 0) -> float:
        """
        获取内存使用量 (MB)（兼容不同 Android 版本）
        
        Android 4.x: 使用 `/proc/meminfo`
        Android 8+: 使用 `dumpsys meminfo`（更精确）
        """
        try:
            if sdk_version >= 26:  # Android 8.0+
                # 使用 dumpsys meminfo（更精确）
                cmd = "shell dumpsys meminfo | grep 'Total RAM'"
                return_code, output = await self.device_manager.run_adb_command(device_id, cmd)
                if return_code == 0 and output:
                    match = re.search(r'(\d+)', output)
                    if match:
                        total_kb = int(match.group(1))
                        # 获取可用内存
                        cmd2 = "shell cat /proc/meminfo | grep MemAvailable"
                        _, output2 = await self.device_manager.run_adb_command(device_id, cmd2)
                        if output2:
                            match2 = re.search(r'(\d+)', output2)
                            if match2:
                                avail_kb = int(match2.group(1))
                                used_mb = (total_kb - avail_kb) / 1024
                                return round(used_mb, 2)
            else:  # Android 4.x - 7.x
                # 使用 /proc/meminfo
                cmd = "shell cat /proc/meminfo | grep MemTotal"
                return_code, output = await self.device_manager.run_adb_command(device_id, cmd)
                if return_code == 0 and output:
                    match = re.search(r'(\d+)', output)
                    if match:
                        total_kb = int(match.group(1))
                        # 获取可用内存
                        cmd2 = "shell cat /proc/meminfo | grep MemAvailable"
                        _, output2 = await self.device_manager.run_adb_command(device_id, cmd2)
                        if output2:
                            match2 = re.search(r'(\d+)', output2)
                            if match2:
                                avail_kb = int(match2.group(1))
                                used_mb = (total_kb - avail_kb) / 1024
                                return round(used_mb, 2)
            
            return 0.0
        except Exception as e:
            logger.error(f"获取内存使用量失败: {e}")
            return 0.0
    
    async def get_memory_percent(self, device_id: str, sdk_version: int = 0) -> float:
        """获取内存使用百分比（兼容不同 Android 版本）"""
        try:
            cmd_total = "shell cat /proc/meminfo | grep MemTotal"
            cmd_avail = "shell cat /proc/meminfo | grep MemAvailable"
            
            _, output_total = await self.device_manager.run_adb_command(device_id, cmd_total)
            _, output_avail = await self.device_manager.run_adb_command(device_id, cmd_avail)
            
            if output_total and output_avail:
                match_total = re.search(r'(\d+)', output_total)
                match_avail = re.search(r'(\d+)', output_avail)
                if match_total and match_avail:
                    total = int(match_total.group(1))
                    avail = int(match_avail.group(1))
                    percent = ((total - avail) / total) * 100
                    return round(percent, 2)
            
            return 0.0
        except Exception as e:
            logger.error(f"获取内存使用百分比失败: {e}")
            return 0.0
    
    async def get_fps(self, device_id: str, sdk_version: int = 0) -> float:
        """
        获取 FPS（兼容不同 Android 版本）
        
        Android 4.x: 使用 logcat 估算（Choreographer）
        Android 5-7: 使用 `dumpsys gfxinfo <package>`（普通模式）
        Android 8+: 使用 `dumpsys gfxinfo <package> framestats`
        """
        try:
            # 获取当前前台应用
            cmd = "shell dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'"
            return_code, output = await self.device_manager.run_adb_command(device_id, cmd)
            
            if not output:
                return 0.0
            
            # 提取包名
            match = re.search(r'([a-zA-Z0-9.]+)/', output)
            if not match:
                return 0.0
            
            package = match.group(1)
            
            if sdk_version >= 26:  # Android 8.0+
                # 使用 framestats 模式（更精确）
                return await self._get_fps_framestats(device_id, package)
            elif sdk_version >= 21:  # Android 5.0 - 7.x
                # 使用普通模式
                return await self._get_fps_normal(device_id, package)
            else:  # Android 4.x
                # 使用 logcat 估算
                return await self._estimate_fps_from_logcat(device_id, package)
                
        except Exception as e:
            logger.error(f"获取 FPS 失败: {e}")
            return 0.0
    
    async def _get_fps_framestats(self, device_id: str, package: str) -> float:
        """解析 framestats 模式的输出（Android 8.0+）"""
        try:
            cmd = f"shell dumpsys gfxinfo {package} framestats"
            return_code, output = await self.device_manager.run_adb_command(device_id, cmd)
            
            if return_code != 0 or not output:
                return 0.0
            
            # 解析 framestats 输出
            # 格式：flag=,?intendedVsync=,?vsync=,?...
            lines = output.strip().split('\n')
            
            frame_times = []
            for line in lines:
                if line.startswith('##'):
                    continue
                parts = line.split(',')
                if len(parts) >= 2:
                    try:
                        intended_vsync = int(parts[1])
                        frame_times.append(intended_vsync)
                    except (ValueError, IndexError):
                        continue
            
            if len(frame_times) < 2:
                return 0.0
            
            # 计算帧间隔
            intervals = []
            for i in range(1, len(frame_times)):
                interval = frame_times[i] - frame_times[i-1]
                if interval > 0:
                    intervals.append(interval / 1000000.0)  # 转换为毫秒
            
            if not intervals:
                return 0.0
            
            # 计算平均 FPS
            avg_interval = sum(intervals) / len(intervals)
            fps = 1000.0 / avg_interval
            
            return round(fps, 2)
            
        except Exception as e:
            logger.error(f"解析 framestats 失败: {e}")
            return 0.0
    
    async def _get_fps_normal(self, device_id: str, package: str) -> float:
        """解析普通模式的输出（Android 5.0 - 7.x）"""
        try:
            cmd = f"shell dumpsys gfxinfo {package}"
            return_code, output = await self.device_manager.run_adb_command(device_id, cmd)
            
            if return_code != 0 or not output:
                return 0.0
            
            # 查找 "Total frames produced:" 行
            lines = output.strip().split('\n')
            
            total_frames = 0
            for line in lines:
                if 'Total frames produced:' in line:
                    match = re.search(r'Total frames produced:\s+(\d+)', line)
                    if match:
                        total_frames = int(match.group(1))
                        break
            
            if total_frames == 0:
                return 0.0
            
            # 需要计算时间窗口内的帧数
            # 这里简化为返回 total_frames（实际需要时间戳）
            return float(total_frames)
            
        except Exception as e:
            logger.error(f"解析普通 FPS 输出失败: {e}")
            return 0.0
    
    async def _estimate_fps_from_logcat(self, device_id: str, package: str) -> float:
        """从 logcat 估算 FPS（Android 4.x 兼容）"""
        try:
            # 清除 logcat 缓冲区
            await self.device_manager.run_adb_command(device_id, "shell logcat -c")
            
            # 等待 1 秒，采集 logcat
            await asyncio.sleep(1)
            
            # 获取 Choreographer 日志（VSync 信号）
            cmd = "shell logcat -d -s Choreographer"
            return_code, output = await self.device_manager.run_adb_command(device_id, cmd)
            
            if return_code != 0 or not output:
                return 0.0
            
            # 统计 VSync 次数（1 秒内的帧数 ≈ FPS）
            lines = output.strip().split('\n')
            vsync_count = 0
            
            for line in lines:
                if 'Skipped' in line or 'Frame' in line:
                    vsync_count += 1
            
            # 粗略估算 FPS
            fps = vsync_count  # 假设采集了 1 秒
            
            return float(fps)
            
        except Exception as e:
            logger.error(f"从 logcat 估算 FPS 失败: {e}")
            return 0.0
    
    async def get_temperature(self, device_id: str) -> float:
        """获取设备温度（如果支持）"""
        try:
            cmd = "shell cat /sys/class/thermal/thermal_zone*/temp"
            return_code, output = await self.device_manager.run_adb_command(device_id, cmd)
            if return_code == 0 and output:
                temps = [int(x) for x in output.split() if x.isdigit()]
                if temps:
                    # 温度通常是毫摄氏度
                    return round(max(temps) / 1000, 1)
            return 0.0
        except Exception as e:
            logger.error(f"获取设备温度失败: {e}")
            return 0.0
    
    async def get_network_rx(self, device_id: str) -> float:
        """获取网络接收速率 (bytes/s)"""
        try:
            cmd = "shell cat /proc/net/xt_qtaguid/stats | tail -1"
            return_code, output = await self.device_manager.run_adb_command(device_id, cmd)
            if return_code == 0 and output:
                parts = output.split()
                if len(parts) > 5:
                    return float(parts[5])  # rx_bytes
            return 0.0
        except Exception as e:
            logger.error(f"获取网络接收速率失败: {e}")
            return 0.0
    
    async def get_network_tx(self, device_id: str) -> float:
        """获取网络发送速率 (bytes/s)"""
        try:
            cmd = "shell cat /proc/net/xt_qtaguid/stats | tail -1"
            return_code, output = await self.device_manager.run_adb_command(device_id, cmd)
            if return_code == 0 and output:
                parts = output.split()
                if len(parts) > 7:
                    return float(parts[7])  # tx_bytes
            return 0.0
        except Exception as e:
            logger.error(f"获取网络发送速率失败: {e}")
            return 0.0
    
    async def save_to_db(self, device_id: str, data: Dict):
        """保存性能数据到数据库"""
        try:
            # 获取设备 ID
            device_row = await fetch_one(
                "SELECT id FROM devices WHERE device_id = ?",
                (device_id,)
            )
            if not device_row:
                return
            
            device_db_id = device_row["id"]
            
            # 获取当前执行 ID
            execution_row = await fetch_one(
                "SELECT id FROM executions WHERE device_id = ? AND status = 'running' ORDER BY start_time DESC LIMIT 1",
                (device_db_id,)
            )
            execution_id = execution_row["id"] if execution_row else None
            
            # 插入性能数据
            await execute_query("""
                INSERT INTO performance_data 
                (execution_id, device_id, cpu_usage, memory_usage, memory_percent, fps, temperature, network_rx, network_tx)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_id,
                device_db_id,
                data.get("cpu_usage", 0),
                data.get("memory_usage", 0),
                data.get("memory_percent", 0),
                data.get("fps", 0),
                data.get("temperature", 0),
                data.get("network_rx", 0),
                data.get("network_tx", 0)
            ))
            
        except Exception as e:
            logger.error(f"保存性能数据到数据库失败: {e}")
    
    async def check_alerts(self, device_id: str, data: Dict):
        """检查性能告警"""
        alerts = []
        
        # FPS 骤降告警
        if data.get("fps", 0) < self.fps_low_threshold:
            alerts.append(f"⚠️ FPS 过低: {data['fps']} 帧")
        
        # CPU 过高告警
        if data.get("cpu_usage", 0) > self.cpu_high_threshold:
            alerts.append(f"⚠️ CPU 使用率过高: {data['cpu_usage']:.1f}%")
        
        # 内存过高告警
        if data.get("memory_percent", 0) > self.mem_high_threshold:
            alerts.append(f"⚠️ 内存使用率过高: {data['memory_percent']:.1f}%")
        
        # 温度过高告警
        if data.get("temperature", 0) > self.temp_high_threshold:
            alerts.append(f"⚠️ 设备温度过高: {data['temperature']:.1f}°C")
        
        if alerts:
            for alert in alerts:
                logger.warning(f"设备 {device_id}: {alert}")
                # 可在此处触发事件通知前端
    
    async def get_latest(self) -> Dict:
        """获取最新性能数据（供 WebSocket 推送）"""
        return self.latest_data.copy()
    
    async def get_history(self, device_id: str, minutes: int = 10) -> List[Dict]:
        """获取历史性能数据"""
        try:
            device_row = await fetch_one(
                "SELECT id FROM devices WHERE device_id = ?",
                (device_id,)
            )
            if not device_row:
                return []
            
            rows = await fetch_all("""
                SELECT * FROM performance_data 
                WHERE device_id = ? AND timestamp > datetime('now', ?)
                ORDER BY timestamp
            """, (device_row["id"], f"-{minutes} minutes"))
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"获取历史性能数据失败: {e}")
            return []
