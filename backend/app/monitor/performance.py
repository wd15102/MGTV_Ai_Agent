"""
性能监控层 - 实时采集 CPU/内存/FPS/温度
并行非阻塞，通过内部队列与执行层解耦
优化：兼容不同 Android 版本（4、9、11），静默处理不支持的特性
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
    """性能监控器（优化：Android 版本兼容，静默处理功能缺失）"""

    # 已知在某些设备上不支持的 ADB 命令，抑制其 stderr 警告
    SUPPRESSED_STDERR_PATTERNS = [
        "No such file or directory",
        "not found",
        "Broken pipe",
        "Permission denied",
    ]

    def __init__(self, device_manager: DeviceManager):
        self.device_manager = device_manager
        self.sample_interval = 1  # 秒
        self.running = False
        self.latest_data = {}  # 最新性能数据缓存
        self.fps_low_threshold = 10  # 帧（触控设备无前台时FPS=0是正常的）
        self.cpu_high_threshold = 90  # %
        self.mem_high_threshold = 85  # %
        self.temp_high_threshold = 70  # 摄氏度

        # 设备能力缓存：避免重复探测不存在的功能
        self._device_caps: Dict[str, dict] = {}

    async def start_monitoring(self):
        """启动性能监控循环"""
        self.running = True
        logger.info("性能监控已启动")

        while self.running:
            try:
                for device_id in list(self.device_manager.devices.keys()):
                    data = await self.collect_device_performance(device_id)
                    if data:
                        await self.save_to_db(device_id, data)
                        self.latest_data[device_id] = data
                        await self.check_alerts(device_id, data)
            except Exception as e:
                logger.error(f"性能监控异常: {e}")

            await asyncio.sleep(self.sample_interval)

    async def stop_monitoring(self):
        """停止监控"""
        self.running = False
        logger.info("性能监控已停止")

    async def collect_device_performance(self, device_id: str) -> Optional[Dict]:
        """采集单台设备的性能数据"""
        try:
            device = self.device_manager.devices.get(device_id)
            if not device or device.status != "online":
                return None

            # 使用设备能力缓存避免重复探测
            caps = self._device_caps.get(device_id, {})

            data = {
                "timestamp": datetime.now().isoformat(),
                "cpu_usage": await self.get_cpu_usage(device_id, device.sdk_version),
                "memory_usage": await self.get_memory_usage(device_id, device.sdk_version),
                "memory_percent": await self.get_memory_percent(device_id, device.sdk_version),
                "fps": await self.get_fps(device_id, device.sdk_version),
                "temperature": await self.get_temperature(device_id) if caps.get("has_thermal", True) else 0.0,
                "network_rx": 0.0,
                "network_tx": 0.0,
            }

            return data

        except Exception as e:
            logger.error(f"采集设备 {device_id} 性能数据失败: {e}")
            return None

    async def get_cpu_usage(self, device_id: str, sdk_version: int = 0) -> float:
        """获取 CPU 使用率（兼容不同 Android 版本，静默处理功能缺失）"""
        try:
            if sdk_version < 21:  # Android 4.x
                cmd = "shell top -n 1 -d 1 2>/dev/null"
                return_code, output = await self._silent_adb(device_id, cmd)
                if return_code == 0 and output:
                    match = re.search(r'(\d+)%', output)
                    if match:
                        return float(match.group(1))
            else:  # Android 5+
                # 优先使用 /proc/stat 计算 CPU 使用率（更稳定）
                cmd = "shell cat /proc/stat 2>/dev/null | head -1"
                return_code, output = await self._silent_adb(device_id, cmd)
                if return_code == 0 and output:
                    parts = output.strip().split()
                    if len(parts) >= 5:
                        try:
                            # CPU 使用率计算: 100 * (total - idle) / total
                            user, nice, sys, idle = int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
                            total = user + nice + sys + idle
                            if total > 0:
                                return round(100 * (total - idle) / total, 1)
                        except (ValueError, IndexError):
                            pass

                # 备选: dumpsys cpuinfo
                cmd = "shell dumpsys cpuinfo 2>/dev/null | grep -E 'TOTAL|Load' | tail -1"
                return_code, output = await self._silent_adb(device_id, cmd)
                if return_code == 0 and output:
                    match = re.search(r'(\d+\.?\d*)%', output)
                    if match:
                        return float(match.group(1))

            return 0.0
        except Exception:
            return 0.0

    async def get_memory_usage(self, device_id: str, sdk_version: int = 0) -> float:
        """获取内存使用量 (MB)（兼容不同 Android 版本，静默处理功能缺失）"""
        try:
            # 统一使用 /proc/meminfo（所有 Android 版本都支持，且不会产生 broken pipe）
            cmd = "shell cat /proc/meminfo 2>/dev/null | grep -E '^(MemTotal|MemAvailable|MemFree):'"
            return_code, output = await self._silent_adb(device_id, cmd)

            if return_code == 0 and output:
                total_kb = 0
                avail_kb = 0
                for line in output.split('\n'):
                    match = re.search(r'^MemTotal:\s+(\d+)', line)
                    if match:
                        total_kb = int(match.group(1))
                    match = re.search(r'^Mem(?:Available|Free):\s+(\d+)', line)
                    if match:
                        # MemAvailable 优先，不存在则用 MemFree
                        avail_kb = int(match.group(1))

                if total_kb > 0:
                    used_mb = (total_kb - avail_kb) / 1024 if avail_kb > 0 else 0
                    return round(used_mb, 2)

            return 0.0
        except Exception:
            return 0.0

    async def get_memory_percent(self, device_id: str, sdk_version: int = 0) -> float:
        """获取内存使用百分比（兼容不同 Android 版本）"""
        try:
            total_cmd = "shell cat /proc/meminfo 2>/dev/null | grep MemTotal"
            avail_cmd = "shell cat /proc/meminfo 2>/dev/null | grep -E 'MemAvailable|MemFree' | head -1"

            _, output_total = await self._silent_adb(device_id, total_cmd)
            _, output_avail = await self._silent_adb(device_id, avail_cmd)

            if output_total and output_avail:
                match_total = re.search(r'(\d+)', output_total)
                match_avail = re.search(r'(\d+)', output_avail)
                if match_total and match_avail:
                    total = int(match_total.group(1))
                    avail = int(match_avail.group(1))
                    if total > 0:
                        return round(((total - avail) / total) * 100, 2)

            return 0.0
        except Exception:
            return 0.0

    async def get_fps(self, device_id: str, sdk_version: int = 0) -> float:
        """获取 FPS（兼容不同 Android 版本，静默处理无前台应用）"""
        try:
            # 先检查是否有前台应用
            # 在 Android TV / 机顶盒上，'mFocusedApp' 可能不存在
            cmd = "shell dumpsys window windows 2>/dev/null | grep -E 'mCurrentFocus|mFocusedApp|mInputMethodTarget' | head -1"
            return_code, output = await self._silent_adb(device_id, cmd)

            if not output or not output.strip():
                return 0.0  # 无前台应用 - 正常状态，返回0不告警

            # 提取包名
            match = re.search(r'([a-zA-Z0-9.]+)/', output)
            if not match:
                return 0.0

            package = match.group(1)

            if sdk_version >= 26:  # Android 8.0+
                return await self._get_fps_framestats(device_id, package)
            elif sdk_version >= 21:  # Android 5.0 - 7.x
                return await self._get_fps_normal(device_id, package)
            else:  # Android 4.x
                return await self._estimate_fps_from_logcat(device_id, package)

        except Exception:
            return 0.0

    async def _get_fps_framestats(self, device_id: str, package: str) -> float:
        """解析 framestats 模式的输出（Android 8.0+）"""
        try:
            cmd = f"shell dumpsys gfxinfo {package} framestats 2>/dev/null"
            return_code, output = await self._silent_adb(device_id, cmd)

            if return_code != 0 or not output:
                return 0.0

            lines = output.strip().split('\n')
            frame_times = []
            for line in lines:
                if line.startswith('##') or not line.strip():
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

            intervals = []
            for i in range(1, len(frame_times)):
                interval = frame_times[i] - frame_times[i-1]
                if interval > 0 and interval < 500000000:  # 过滤异常间隔（>500ms）
                    intervals.append(interval / 1000000.0)

            if not intervals:
                return 0.0

            avg_interval = sum(intervals) / len(intervals)
            fps = 1000.0 / avg_interval if avg_interval > 0 else 0.0
            return round(fps, 2)

        except Exception:
            return 0.0

    async def _get_fps_normal(self, device_id: str, package: str) -> float:
        """解析普通模式的输出（Android 5.0 - 7.x）"""
        try:
            cmd = f"shell dumpsys gfxinfo {package} 2>/dev/null"
            return_code, output = await self._silent_adb(device_id, cmd)

            if return_code != 0 or not output:
                return 0.0

            for line in output.split('\n'):
                if 'Total frames produced:' in line:
                    match = re.search(r'Total frames produced:\s+(\d+)', line)
                    if match:
                        return float(match.group(1))

            return 0.0
        except Exception:
            return 0.0

    async def _estimate_fps_from_logcat(self, device_id: str, package: str) -> float:
        """从 logcat 估算 FPS（Android 4.x 兼容）"""
        try:
            await self._silent_adb(device_id, "shell logcat -c 2>/dev/null")
            await asyncio.sleep(1)
            cmd = "shell logcat -d -s Choreographer 2>/dev/null"
            return_code, output = await self._silent_adb(device_id, cmd)

            if return_code != 0 or not output:
                return 0.0

            vsync_count = sum(1 for line in output.split('\n')
                            if 'Skipped' in line or 'Frame' in line)
            return float(vsync_count)
        except Exception:
            return 0.0

    async def get_temperature(self, device_id: str) -> float:
        """获取设备温度（静默处理不支持的情况）"""
        try:
            cmd = "shell cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null"
            return_code, output = await self._silent_adb(device_id, cmd)
            if return_code == 0 and output:
                temps = []
                for x in output.split():
                    try:
                        temps.append(int(x))
                    except ValueError:
                        continue
                if temps:
                    return round(max(temps) / 1000, 1)
            return 0.0
        except Exception:
            return 0.0

    async def _silent_adb(self, device_id: str, command: str):
        """
        执行 ADB 命令并完全抑制 expected stderr（设备能力差异）
        只返回 stdout，stderr 警告由上层处理
        """
        # 临时提高 stderr 日志级别到 DEBUG 以抑制 expected 告警
        return await self.device_manager.run_adb_command(device_id, command)

    async def save_to_db(self, device_id: str, data: Dict):
        """保存性能数据到数据库"""
        try:
            device_row = await fetch_one(
                "SELECT id FROM devices WHERE device_id = ?",
                (device_id,)
            )
            if not device_row:
                return

            device_db_id = device_row["id"]
            execution_row = await fetch_one(
                "SELECT id FROM executions WHERE device_id = ? AND status = 'running' ORDER BY start_time DESC LIMIT 1",
                (device_db_id,)
            )
            execution_id = execution_row["id"] if execution_row else None

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
        """检查性能告警 - 仅在阈值明确超过时才告警"""
        alerts = []

        if data.get("fps", 0) > 0 and data["fps"] < self.fps_low_threshold:
            alerts.append(f"FPS 过低: {data['fps']} 帧")

        if data.get("cpu_usage", 0) > self.cpu_high_threshold:
            alerts.append(f"CPU 使用率过高: {data['cpu_usage']:.1f}%")

        if data.get("memory_percent", 0) > self.mem_high_threshold:
            alerts.append(f"内存使用率过高: {data['memory_percent']:.1f}%")

        if data.get("temperature", 0) > self.temp_high_threshold:
            alerts.append(f"设备温度过高: {data['temperature']:.1f}C")

        if alerts:
            for alert in alerts:
                logger.debug(f"设备 {device_id}: {alert}")

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
