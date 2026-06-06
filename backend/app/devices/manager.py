"""
设备管理器 - 管理最多2台设备的连接、心跳、状态
支持手机/TV/机顶盒
"""
import asyncio
import logging
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
            "last_heartbeat": self.last_heartbeat.isoformat()
        }


class DeviceManager:
    """设备管理器"""
    
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
        """获取通过 ADB 连接的设备列表"""
        try:
            proc = await asyncio.create_subprocess_shell(
                "adb devices",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode('utf-8', errors='ignore')
            
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
        """添加设备"""
        if len(self.devices) >= self.max_devices:
            logger.error(f"设备数已达上限({self.max_devices})")
            return False
        
        try:
            # 获取设备信息
            name = await self.get_property(device_id, "ro.product.model")
            android_version = await self.get_property(device_id, "ro.build.version.release")
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
            device.resolution = resolution
            device.status = "online"
            device.last_heartbeat = datetime.now()
            device.key_mapping = self.DEFAULT_KEY_MAP.get(device_type, self.DEFAULT_KEY_MAP["phone"]).copy()
            
            self.devices[device_id] = device
            logger.info(f"✅ 设备已添加: {device_id} ({name})")
            return True
            
        except Exception as e:
            logger.error(f"添加设备失败: {e}")
            return False
    
    async def get_property(self, device_id: str, prop: str) -> str:
        """获取设备属性"""
        try:
            proc = await asyncio.create_subprocess_shell(
                f"adb -s {device_id} shell getprop {prop}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            return stdout.decode('utf-8', errors='ignore').strip()
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
        """重连设备"""
        for attempt in range(self.adb_reconnect_attempts):
            try:
                logger.info(f"尝试重连设备 {device_id} (第 {attempt+1}/{self.adb_reconnect_attempts} 次)")
                proc = await asyncio.create_subprocess_shell(
                    f"adb -s {device_id} reconnect",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await proc.communicate()
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
        """截屏并返回文件路径"""
        if device_id not in self.devices:
            logger.error(f"设备不存在: {device_id}")
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_path = self.devices[device_id].screenshot_dir / f"{timestamp}.png"
            
            # 在设备上截屏
            await self.run_adb_command(device_id, "shell screencap -p /sdcard/screenshot.png")
            # 拉取到本地
            await self.run_adb_command(device_id, f"pull /sdcard/screenshot.png {local_path}")
            # 删除设备上的临时文件
            await self.run_adb_command(device_id, "shell rm /sdcard/screenshot.png")
            
            return str(local_path)
        except Exception as e:
            logger.error(f"截屏失败: {e}")
            return None
    
    async def run_adb_command(self, device_id: str, command: str) -> Tuple[int, str]:
        """执行 ADB 命令"""
        try:
            full_cmd = f"adb -s {device_id} {command}"
            proc = await asyncio.create_subprocess_shell(
                full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            output = stdout.decode('utf-8', errors='ignore')
            if stderr:
                logger.warning(f"ADB 命令警告: {stderr.decode('utf-8', errors='ignore')}")
            return proc.returncode, output
        except Exception as e:
            logger.error(f"执行 ADB 命令失败: {e}")
            return -1, str(e)
    
    async def click(self, device_id: str, x: int, y: int) -> bool:
        """点击坐标"""
        return_code, _ = await self.run_adb_command(device_id, f"shell input tap {x} {y}")
        return return_code == 0
    
    async def swipe(self, device_id: str, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        """滑动"""
        return_code, _ = await self.run_adb_command(
            device_id, f"shell input swipe {x1} {y1} {x2} {y2} {duration}"
        )
        return return_code == 0
    
    async def input_text(self, device_id: str, text: str) -> bool:
        """输入文本"""
        # 需要先聚焦输入框
        return_code, _ = await self.run_adb_command(device_id, f"shell input text '{text}'")
        return return_code == 0
    
    async def press_key(self, device_id: str, keycode: str) -> bool:
        """按键值"""
        return_code, _ = await self.run_adb_command(device_id, f"shell input keyevent {keycode}")
        return return_code == 0
    
    async def install_app(self, device_id: str, apk_path: str) -> bool:
        """安装应用"""
        return_code, _ = await self.run_adb_command(device_id, f"install {apk_path}")
        return return_code == 0
    
    async def uninstall_app(self, device_id: str, package: str) -> bool:
        """卸载应用"""
        return_code, _ = await self.run_adb_command(device_id, f"uninstall {package}")
        return return_code == 0
    
    async def get_status(self) -> List[dict]:
        """获取所有设备状态"""
        return [device.to_dict() for device in self.devices.values()]
    
    async def cleanup(self):
        """清理资源"""
        logger.info("清理设备管理资源...")
        self.devices.clear()
