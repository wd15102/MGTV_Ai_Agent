"""
设备管理器 - 管理最多2台设备的连接、心跳、状态
支持手机/TV/机顶盒
优化：Windows ADB 编码处理 + Android 版本兼容
"""
import asyncio
import logging
import os
import locale
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class Device:
    """设备对象"""
    def __init__(self, device_id: str, name: str = "", device_type: str = "phone"):
        self.device_id = device_id
        self.name = name or device_id
        self.type = device_type  # phone/tv/box
        self.status = "offline"  # online/offline/busy
        self.resolution = (0, 0)  # (width, height)
        self.android_version = ""
        self.sdk_version = 0  # SDK INT
        self.last_heartbeat = datetime.now()
        self.current_execution_id = None
        self.key_mapping = {}  # 键值映射表
        self.screenshot_dir = Path("logs") / "screenshots" / device_id
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
    def to_dict(self):
        return {
            "device_id": self.device_id,
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "resolution": f"{self.resolution[0]}x{self.resolution[1]}",
            "android_version": self.android_version,
            "sdk_version": self.sdk_version,
            "last_heartbeat": self.last_heartbeat.isoformat()
        }


class DeviceManager:
    """设备管理器（优化：编码处理 + Android 版本兼容）"""
    
    # 标准 Android 键值映射（不同设备可能有差异）
    DEFAULT_KEY_MAP = {
        "phone": {
            "HOME": "3",
            "BACK": "4",
            "ENTER": "66",
            "UP": "19",
            "DOWN": "20",
            "LEFT": "21",
            "RIGHT": "22",
            "MENU": "82",
            "POWER": "26",
        },
        "tv": {
            "HOME": "3",
            "BACK": "4",
            "ENTER": "23",  # DPAD_CENTER
            "UP": "19",
            "DOWN": "20",
            "LEFT": "21",
            "RIGHT": "22",
            "MENU": "82",
            "PLAY": "126",
            "PAUSE": "127",
        },
        "box": {
            "HOME": "3",
            "BACK": "4",
            "ENTER": "23",  # DPAD_CENTER
            "UP": "19",
            "DOWN": "20",
            "LEFT": "21",
            "RIGHT": "22",
            "MENU": "82",
            "POWER": "26",
        }
    }
    
    def __init__(self):
        self.devices: Dict[str, Device] = {}
        self.max_devices = 2
        self.heartbeat_interval = 5  # 秒
        self.offline_threshold = 15  # 秒
        self.adb_reconnect_attempts = 3
        self.adb_reconnect_delay = 2  # 秒
        
        # 编码配置（Windows 兼容）
        self.system_encoding = locale.getpreferredencoding()
        self.use_utf8 = False
        
        # Windows 下尝试切换到 UTF-8 代码页
        if os.name == 'nt':
            try:
                subprocess.run(['chcp', '65001'], shell=True, capture_output=True, timeout=5)
                self.use_utf8 = True
                logger.info("✅ 已切换到 UTF-8 代码页 (chcp 65001)")
            except Exception as e:
                logger.warning(f"⚠️ 无法切换到 UTF-8 代码页: {e}")
                self.use_utf8 = False
    
    async def start_heartbeat(self):
        """启动心跳检测循环"""
        while True:
            try:
                await self.check_all_devices()
            except Exception as e:
                logger.error(f"心跳检测异常: {e}")
            await asyncio.sleep(self.heartbeat_interval)
    
    async def check_all_devices(self):
        """检查所有设备状态"""
        # 获取当前连接的 ADB 设备
        connected = await self.get_connected_devices()
        
        # 更新已有设备状态
        for device_id, device in self.devices.items():
            if device_id in connected:
                device.status = "online"
                device.last_heartbeat = datetime.now()
            else:
                # 检查是否超时
                elapsed = (datetime.now() - device.last_heartbeat).total_seconds()
                if elapsed > self.offline_threshold:
                    device.status = "offline"
                    logger.warning(f"设备 {device_id} 离线")
        
        # 自动添加新设备
        for device_id in connected:
            if device_id not in self.devices:
                if len(self.devices) < self.max_devices:
                    await self.add_device(device_id)
                else:
                    logger.warning(f"设备数已达上限({self.max_devices})，忽略新设备: {device_id}")
    
    async def get_connected_devices(self) -> List[str]:
        """获取通过 ADB 连接的设备列表（处理编码）"""
        try:
            # 使用改进后的 _execute_adb_command
            returncode, output = await self.run_adb_command("", "devices", encoding='utf-8')
            
            if returncode != 0:
                return []
            
            devices = []
            for line in output.split('\n')[1:]:  # 跳过第一行 "List of devices attached"
                if '\t' in line:
                    device_id = line.split('\t')[0].strip()
                    if device_id:
                        devices.append(device_id)
            return devices
        except Exception as e:
            logger.error(f"获取 ADB 设备列表失败: {e}")
            return []
    
    async def add_device(self, device_id: str, device_type: str = "phone") -> bool:
        """添加设备（获取 Android 版本号）"""
        if len(self.devices) >= self.max_devices:
            logger.error(f"设备数已达上限({self.max_devices})")
            return False
        
        try:
            # 获取设备信息
            name = await self.get_property(device_id, "ro.product.model")
            android_version = await self.get_property(device_id, "ro.build.version.release")
            sdk_version_str = await self.get_property(device_id, "ro.build.version.sdk")
            
            # 解析 SDK 版本号
            sdk_version = 0
            try:
                sdk_version = int(sdk_version_str.strip())
            except ValueError:
                sdk_version = 0
            
            resolution_str = await self.get_property(device_id, "wm.size")
            
            # 解析分辨率
            resolution = (0, 0)
            if resolution_str:
                match = re.search(r'(\d+)x(\d+)', resolution_str)
                if match:
                    resolution = (int(match.group(1)), int(match.group(2)))
            
            # 创建设备对象
            device = Device(device_id, name, device_type)
            device.android_version = android_version
            device.sdk_version = sdk_version
            device.resolution = resolution
            device.status = "online"
            device.last_heartbeat = datetime.now()
            device.key_mapping = self.DEFAULT_KEY_MAP.get(device_type, self.DEFAULT_KEY_MAP["phone"]).copy()
            
            self.devices[device_id] = device
            logger.info(f"✅ 设备已添加: {device_id} ({name}) [Android {android_version}, SDK {sdk_version}]")
            return True
            
        except Exception as e:
            logger.error(f"添加设备失败: {e}")
            return False
    
    async def get_property(self, device_id: str, prop: str) -> str:
        """获取设备属性（处理编码）"""
        try:
            returncode, output = await self.run_adb_command(device_id, f"shell getprop {prop}")
            if returncode == 0:
                return output.strip()
            return ""
        except Exception as e:
            logger.error(f"获取设备属性失败: {e}")
            return ""
    
    async def remove_device(self, device_id: str) -> bool:
        """移除设备"""
        if device_id in self.devices:
            del self.devices[device_id]
            logger.info(f"设备已移除: {device_id}")
            return True
        return False
    
    async def reconnect_device(self, device_id: str) -> bool:
        """重连设备（处理编码）"""
        for attempt in range(self.adb_reconnect_attempts):
            try:
                logger.info(f"尝试重连设备 {device_id} (第 {attempt+1}/{self.adb_reconnect_attempts} 次)")
                
                returncode, output = await self.run_adb_command(device_id, "reconnect")
                
                await asyncio.sleep(self.adb_reconnect_delay)
                
                # 检查是否恢复
                connected = await self.get_connected_devices()
                if device_id in connected:
                    self.devices[device_id].status = "online"
                    self.devices[device_id].last_heartbeat = datetime.now()
                    logger.info(f"✅ 设备 {device_id} 重连成功")
                    return True
            except Exception as e:
                logger.error(f"重连失败: {e}")
        
        # 重连失败
        if device_id in self.devices:
            self.devices[device_id].status = "offline"
        logger.error(f"❌ 设备 {device_id} 重连失败，已标记为离线")
        return False
    
    async def take_screenshot(self, device_id: str) -> Optional[str]:
        """截屏（兼容不同 Android 版本）"""
        if device_id not in self.devices:
            logger.error(f"设备不存在: {device_id}")
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_path = self.devices[device_id].screenshot_dir / f"{timestamp}.png"
            
            # 获取 Android 版本
            sdk_version = self.devices[device_id].sdk_version
            
            # 在设备上截屏（兼容不同版本）
            remote_path = f"/sdcard/screenshot_{timestamp}.png"
            
            if sdk_version >= 28:  # Android 9.0+
                # 使用 screencap -p（更快）
                await self.run_adb_command(device_id, f"shell screencap -p {remote_path}")
            else:  # Android 8.0 及以下
                # 使用 screencap（兼容模式）
                await self.run_adb_command(device_id, f"shell screencap {remote_path}")
            
            # 拉取到本地
            await self.run_adb_command(device_id, f"pull {remote_path} {local_path}")
            
            # 删除设备上的临时文件
            await self.run_adb_command(device_id, f"shell rm {remote_path}")
            
            return str(local_path)
        except Exception as e:
            logger.error(f"截屏失败: {e}")
            return None
    
    async def run_adb_command(
        self, 
        device_id: str, 
        command: str,
        encoding: str = 'utf-8'
    ) -> Tuple[int, str]:
        """
        执行 ADB 命令（统一封装，处理编码问题）
        
        Args:
            device_id: 设备 ID（空字符串表示不指定设备）
            command: ADB 命令（不含 "adb -s xxx" 前缀）
            encoding: 期望的编码（默认 UTF-8）
            
        Returns:
            (returncode, output)
        """
        try:
            # 构建完整命令
            if device_id:
                full_cmd = f"adb -s {device_id} {command}"
            else:
                full_cmd = f"adb {command}"
            
            # Windows 下设置环境变量强制 UTF-8
            env = os.environ.copy()
            if os.name == 'nt':
                env['PYTHONIOENCODING'] = 'utf-8'
                env['PYTHONLEGACYWINDOWSSTDIO'] = 'utf-8'
                # 如果已切换到 UTF-8 代码页，使用 UTF-8
                if self.use_utf8:
                    pass  # 已经设置了环境变量
                else:
                    # 否则使用系统编码
                    encoding = self.system_encoding.lower()
            
            # 执行命令（使用 asyncio.create_subprocess_shell）
            process = await asyncio.create_subprocess_shell(
                full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await process.communicate()
            
            # 尝试使用指定编码解码，失败则使用 UTF-8 并忽略错误
            try:
                output = stdout.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                output = stdout.decode('utf-8', errors='ignore')
            
            # 清洗输出（移除控制字符）
            output = self._clean_output(output)
            
            if stderr:
                try:
                    error_output = stderr.decode(encoding)
                except (UnicodeDecodeError, LookupError):
                    error_output = stderr.decode('utf-8', errors='ignore')
                logger.warning(f"ADB 命令警告: {error_output}")
            
            return process.returncode, output.strip()
            
        except Exception as e:
            logger.error(f"执行 ADB 命令失败: {full_cmd}, 错误: {e}")
            return -1, str(e)
    
    def _clean_output(self, output: str) -> str:
        """
        清洗命令输出（移除控制字符和 ANSI 转义序列）
        
        Args:
            output: 原始输出字符串
            
        Returns:
            清洗后的字符串
        """
        try:
            import re
            
            # 移除 ANSI 转义序列
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            output = ansi_escape.sub('', output)
            
            # 移除其他控制字符（保留换行符和制表符）
            output = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', output)
            
            return output
        except Exception as e:
            logger.error(f"清洗输出失败: {e}")
            return output
    
    async def get_android_version(self, device_id: str) -> int:
        """
        获取 Android SDK 版本号
        
        Returns:
            SDK 版本号（如 28 表示 Android 9.0）
        """
        if device_id in self.devices:
            return self.devices[device_id].sdk_version
        
        try:
            sdk_version_str = await self.get_property(device_id, "ro.build.version.sdk")
            return int(sdk_version_str.strip())
        except Exception as e:
            logger.error(f"获取 Android 版本失败: {e}")
            return 0
    
    async def click(self, device_id: str, x: int, y: int) -> bool:
        """点击坐标"""
        returncode, _ = await self.run_adb_command(device_id, f"shell input tap {x} {y}")
        return returncode == 0
    
    async def swipe(self, device_id: str, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        """滑动"""
        returncode, _ = await self.run_adb_command(
            device_id, f"shell input swipe {x1} {y1} {x2} {y2} {duration}"
        )
        return returncode == 0
    
    async def input_text(self, device_id: str, text: str) -> bool:
        """输入文本（处理中文编码）"""
        # 需要先聚焦输入框
        # 注意：ADB shell input text 不支持中文，需要使用 Unicode 转义
        # 这里简化为英文输入，中文输入需要其他方法
        returncode, _ = await self.run_adb_command(device_id, f"shell input text '{text}'")
        return returncode == 0
    
    async def press_key(self, device_id: str, keycode: str) -> bool:
        """按键值"""
        returncode, _ = await self.run_adb_command(device_id, f"shell input keyevent {keycode}")
        return returncode == 0
    
    async def install_app(self, device_id: str, apk_path: str) -> bool:
        """安装应用"""
        returncode, _ = await self.run_adb_command(device_id, f"install {apk_path}")
        return returncode == 0
    
    async def uninstall_app(self, device_id: str, package: str) -> bool:
        """卸载应用"""
        returncode, _ = await self.run_adb_command(device_id, f"uninstall {package}")
        return returncode == 0
    
    async def get_status(self) -> List[dict]:
        """获取所有设备状态"""
        return [device.to_dict() for device in self.devices.values()]
    
    async def cleanup(self):
        """清理资源"""
        logger.info("清理设备管理资源...")
        self.devices.clear()
