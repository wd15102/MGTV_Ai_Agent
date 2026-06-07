"""
scrcpy H.264 硬件编码流读取器

从设备获取 H.264 视频流，解码为 JPEG 帧。
使用 scrcpy-server v3.3.3（来自 QtScrcpy），通过 ADB forward + LocalServerSocket 通信。

协议格式（scrcpy v3.3）：
  1B  dummy (0x00)
 64B  device_name (null-terminated/padded)
 12B  stream_meta (4B codec + 4B width + 4B height, big-endian)
 重复:
  12B  frame_meta (8B PTS/flags + 4B data_size, big-endian)
  nB   frame_data (H.264 Annex-B, size=data_size)
"""

import asyncio
import logging
import os
import socket
import struct
import subprocess
import tempfile
import threading
import time
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---- scrcpy 协议常量 ----

HEADER_SIZE = 65       # 1B dummy + 64B device_name
STREAM_META_SIZE = 12   # 4B codec + 4B width + 4B height
FRAME_META_SIZE = 12    # 8B PTS/flags + 4B data_size
NAL_START_CODE = b'\x00\x00\x00\x01'

# PTS 标志位
SESSION_FLAG = 1 << 63
CONFIG_FLAG = 1 << 62
KEY_FLAG = 1 << 61


def recv_exact(sock: socket.socket, n: int, timeout: float = 1.0) -> Optional[bytes]:
    """
    从 socket 精确读取 n 字节
    
    注意：此函数不会修改 socket 的全局超时。使用 sock.settimeout(timeout) 设置超时，
    完成后恢复原始值。
    
    Returns:
        bytes (长度 n) 或 None（连接断开/错误）
    Raises:
        socket.timeout: 读取超时
    """
    try:
        original_timeout = sock.gettimeout()
    except OSError:
        # socket 已关闭
        return None
    
    sock.settimeout(timeout)
    data = b''
    try:
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data
    finally:
        try:
            sock.settimeout(original_timeout)
        except OSError:
            pass


def find_scrcpy_server() -> Optional[str]:
    """
    自动查找 scrcpy-server 文件路径
    
    查找顺序：
    1. 环境变量 SCRCPY_SERVER
    2. QtScrcpy 目录（常见安装路径）
    3. 当前目录
    """
    # 1. 环境变量
    env_path = os.environ.get("SCRCPY_SERVER")
    if env_path and os.path.isfile(env_path):
        return os.path.abspath(env_path)
    
    # 2. QtScrcpy 目录
    candidates = [
        r"D:\Android\QtScrcpy-win-x64-v3.3.3\scrcpy-server",
        r"D:\Android\QtScrcpy-win-x64-v3.3.3\scrcpy-server",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    
    # 3. 当前目录
    if os.path.isfile("scrcpy-server"):
        return os.path.abspath("scrcpy-server")
    
    return None


class H264FrameDecoder:
    """
    H.264 → JPEG 解码器
    
    使用内存缓冲区暂存 H.264 Annex-B 数据，解码时写到临时文件供 OpenCV 解析。
    """
    
    def __init__(self, max_width: int = 720, max_height: int = 1280):
        self._lock = threading.Lock()
        self._buffer = bytearray()
        self._decoded_count = 0
        self._decoder_frame_count = 0
        self._temp_path = None
    
    def write_data(self, data: bytes):
        """追加 H.264 数据到内存缓冲区"""
        with self._lock:
            self._buffer.extend(data)
    
    def decode_latest(self) -> Optional[bytes]:
        """
        解码最新的可解码帧
        
        将内存缓冲区写入临时文件，通过 OpenCV 逐帧解码。
        每次使用新临时文件避免 OpenCV 读取缓存问题。
        
        Returns:
            JPEG bytes 或 None（无可解码帧）
        """
        try:
            with self._lock:
                buf = bytes(self._buffer)
            
            if len(buf) < 50:
                logger.debug(f"[H264Decoder] 缓冲区太小 ({len(buf)}B)，跳过解码")
                return None
            
            logger.debug(f"[H264Decoder] 解码: buf={len(buf)}B")
            
            # 清理旧临时文件
            if self._temp_path and os.path.exists(self._temp_path):
                try:
                    os.remove(self._temp_path)
                except:
                    pass
            
            # 写到新临时文件
            import uuid
            self._temp_path = os.path.join(
                tempfile.gettempdir(),
                f"scrcpy_h264_{uuid.uuid4().hex}.h264"
            )
            with open(self._temp_path, 'wb') as f:
                f.write(buf)
            
            count = 0
            last_frame = None
            cap = cv2.VideoCapture(self._temp_path, cv2.CAP_ANY)
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                count += 1
                last_frame = frame
            cap.release()
        except Exception as e:
            logger.warning(f"[H264Decoder] decode error: {e}")
            return None
        
        if count > self._decoded_count and last_frame is not None:
            self._decoded_count = count
            self._decoder_frame_count = count
            success, buf = cv2.imencode('.jpg', last_frame, [
                cv2.IMWRITE_JPEG_QUALITY, 80
            ])
            if success:
                return buf.tobytes()
        
        return None
    
    def reset_at_config(self):
        """
        重置解码器
        
        清空内存缓冲区，下一帧起从头重建 H.264 流。
        """
        with self._lock:
            self._buffer = bytearray()
            self._decoded_count = 0
            self._decoder_frame_count = 0
    
    def trim(self, max_bytes: int = 500_000):
        """
        裁剪缓冲区，保留最近 max_bytes 字节
        
        用于周期性缓冲区维护，防止内存无限增长。
        """
        with self._lock:
            if len(self._buffer) > max_bytes:
                self._buffer = self._buffer[-max_bytes:]
    
    def cleanup(self):
        """清理临时文件"""
        if self._temp_path and os.path.exists(self._temp_path):
            try:
                os.remove(self._temp_path)
            except Exception:
                pass


class ScrcpyDeviceStreamReader:
    """
    scrcpy H.264 硬件编码流读取器
    
    接口与 DeviceStreamReader（PNG 方案）一致，可无缝替换。
    
    使用方法：
        reader = ScrcpyDeviceStreamReader(adb_path, device_id, scrcpy_server_path)
        if await reader.start():
            frame = await reader.get_frame()  # bytes: JPEG
            await reader.stop()
    """
    
    # 端口池，避免冲突
    _port_lock = threading.Lock()
    _next_port = 27195
    
    @classmethod
    def _allocate_port(cls) -> int:
        with cls._port_lock:
            port = cls._next_port
            cls._next_port += 1
            return port
    
    def __init__(
        self,
        adb_path: str,
        device_id: str,
        scrcpy_server_path: str = "",
        max_size: int = 720,
        bit_rate: int = 2000000,
        decode_every_n: int = 2,
    ):
        """
        Args:
            adb_path: adb 可执行文件路径
            device_id: 设备 ID (IP:PORT 或序列号)
            scrcpy_server_path: scrcpy-server jar 路径
            max_size: 视频最大尺寸（长边，默认 720p）
            bit_rate: 视频码率（默认 2Mbps）
            decode_every_n: 每 N 帧解码一次（默认 2，节省 CPU）
        """
        self._adb_path = adb_path
        self._device_id = device_id
        self._server_path = scrcpy_server_path or ""
        self._max_size = max_size
        self._bit_rate = bit_rate
        self._decode_interval = decode_every_n
        
        # 运行时状态
        self._local_port = self._allocate_port()
        self._proc: Optional[subprocess.Popen] = None
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        
        # 帧缓冲区（线程安全）
        self._lock = threading.Lock()
        self._latest_frame: Optional[bytes] = None  # JPEG bytes
        self._frame_seq: int = 0          # 帧序列号，每次更新递增
        self._last_returned_seq: int = 0  # 上次返回的帧序列号，用于检测新帧
        self._frame_event = threading.Event()
        
        # H.264 解码器
        self._decoder: Optional[H264FrameDecoder] = None
        
        # 流信息
        self._codec: Optional[str] = None
        self._width: int = 0
        self._height: int = 0
        self._device_name: str = ""
    
    @property
    def stream_info(self) -> dict:
        """返回流信息"""
        return {
            "codec": self._codec or "",
            "width": self._width,
            "height": self._height,
            "device_name": self._device_name,
            "local_port": self._local_port,
        }
    
    async def start(self) -> bool:
        """
        启动 scrcpy 流
        
        步骤:
        1. 清理旧的 ADB forward
        2. 建立 ADB forward (tcp → localabstract:scrcpy)
        3. Push scrcpy-server jar 到设备
        4. 启动 scrcpy-server
        5. TCP 连接（带重试，等待 ~2.5-5s）
        6. 解析协议头
        7. 启动后台解码线程
        """
        if not self._server_path or not os.path.isfile(self._server_path):
            logger.error(f"[ScrcpyReader] scrcpy-server 文件不存在: {self._server_path}")
            return False
        
        # --- 0. 杀设备上残留的 scrcpy-server 进程 ---
        try:
            subprocess.run(
                [self._adb_path, '-s', self._device_id, 'shell',
                 'killall -9 app_process 2>/dev/null; '
                 'kill -9 $(pgrep -f scrcpy) 2>/dev/null; '
                 'echo done'],
                capture_output=True, timeout=5
            )
            await asyncio.sleep(0.3)
        except Exception:
            pass
        
        # --- 1. 清理旧 forward ---
        subprocess.run(
            [self._adb_path, '-s', self._device_id, 'forward', '--remove',
             f'tcp:{self._local_port}'],
            capture_output=True, timeout=5
        )
        
        # --- 2. 建立 ADB forward ---
        fwd = subprocess.run(
            [self._adb_path, '-s', self._device_id, 'forward',
             f'tcp:{self._local_port}', 'localabstract:scrcpy'],
            capture_output=True, timeout=5
        )
        if fwd.returncode != 0:
            logger.error(f"[ScrcpyReader] ADB forward 失败: {fwd.stderr.decode(errors='replace')}")
            return False
        logger.info(f"[ScrcpyReader] ADB forward: tcp:{self._local_port} → localabstract:scrcpy")
        
        # --- 3. Push scrcpy-server ---
        remote_path = "/data/local/tmp/scrcpy-server"
        push = subprocess.run(
            [self._adb_path, '-s', self._device_id, 'push', self._server_path, remote_path],
            capture_output=True, timeout=10
        )
        if push.returncode != 0:
            logger.warning(f"[ScrcpyReader] push 失败（可能已存在）: {push.stderr.decode(errors='replace')}")
        
        # --- 4. 启动 scrcpy-server ---
        server_cmd = (
            f"CLASSPATH={remote_path} "
            f"app_process / com.genymobile.scrcpy.Server 3.3.3 "
            f"scid=-1 tunnel_forward=true video=true audio=false "
            f"control=false max_size={self._max_size} "
            f"video_bit_rate={self._bit_rate} "
            f"send_device_meta=true send_frame_meta=true "
            f"send_dummy_byte=true "
            f"cleanup=false power_on=false"
        )
        
        self._proc = subprocess.Popen(
            [self._adb_path, '-s', self._device_id, 'shell', server_cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # --- 5. TCP 连接（带重试） ---
        # scrcpy-server 需要 2-3s 初始化，连接过早可能落到旧进程残留
        await asyncio.sleep(2.5)
        
        connected = False
        for attempt in range(5):  # 每 0.5s 重试最多 5 次 = 最多 5s
            if self._proc and self._proc.poll() is not None:
                logger.error(f"[ScrcpyReader] ADB shell 进程已退出 (rc={self._proc.returncode})")
                break
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            try:
                sock.connect(('127.0.0.1', self._local_port))
                # 连接成功 -> 不消耗数据，交给后续 recv_exact 解析
                self._sock = sock
                connected = True
                break
            except (ConnectionRefusedError, OSError, socket.timeout):
                sock.close()
            if attempt < 4:
                await asyncio.sleep(0.5)
        
        if not connected:
            logger.error(f"[ScrcpyReader] TCP 连接失败（服务器未在 2.5s+2.5s=5s 内就绪）")
            await self.stop()
            return False
        
        # 连接后在 socket 上设置短超时，使流线程可周期性检查运行状态
        self._sock.settimeout(1.0)
        
        logger.info(f"[ScrcpyReader] TCP 已连接 127.0.0.1:{self._local_port}")
        
        # --- 6. 解析协议头（带重试） ---
        header_ok = False
        for hdr_attempt in range(5):
            if not self._running:
                return False
            try:
                header = recv_exact(self._sock, HEADER_SIZE, timeout=3)
                if header and len(header) >= HEADER_SIZE:
                    self._device_name = header[1:].rstrip(b'\x00').decode('utf-8', errors='replace')
                    logger.info(f"[ScrcpyReader] 设备: '{self._device_name}'")
                    header_ok = True
                    break
                else:
                    logger.warning(f"[ScrcpyReader] 设备头重试 #{hdr_attempt+1}: 收到 {len(header or b'')}B")
            except socket.timeout:
                logger.warning(f"[ScrcpyReader] 设备头重试 #{hdr_attempt+1}: 超时")
            # 断开旧 socket 重连
            try:
                self._sock.close()
            except:
                pass
            await asyncio.sleep(1)
            # 重试 TCP 连接
            try:
                sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock2.settimeout(3)
                sock2.connect(('127.0.0.1', self._local_port))
                self._sock = sock2
                logger.info(f"[ScrcpyReader] 重连 TCP 成功")
            except Exception as e:
                logger.warning(f"[ScrcpyReader] 重连失败: {e}")
        
        if not header_ok:
            logger.error(f"[ScrcpyReader] 设备头读取失败（重试 {5} 次后放弃）")
            await self.stop()
            return False
        
        # 12B 流元数据
        try:
            meta = recv_exact(self._sock, STREAM_META_SIZE, timeout=5)
            if not meta or len(meta) < STREAM_META_SIZE:
                logger.error(f"[ScrcpyReader] 流元数据读取失败")
                await self.stop()
                return False
        except socket.timeout:
            logger.error("[ScrcpyReader] 流元数据读取超时")
            await self.stop()
            return False
        
        self._codec = meta[:4].decode('ascii', errors='replace')
        self._width = int.from_bytes(meta[4:8], 'big')
        self._height = int.from_bytes(meta[8:12], 'big')
        logger.info(f"[ScrcpyReader] 流: {self._codec} {self._width}x{self._height}")
        
        # --- 7. 启动后台解码线程 ---
        self._running = True
        self._decoder = H264FrameDecoder()
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()
        logger.info(f"[ScrcpyReader] 后台线程已启动")
        
        return True
    
    def _reader_loop(self):
        """
        后台线程：持续读取 H.264 帧并解码为 JPEG
        
        负责：
        1. 从 socket 读取帧元数据和帧数据
        2. 将 H.264 数据写入临时文件
        3. 定期通过 OpenCV 解码
        4. 在请求时发送最新的 JPEG 帧
        """
        logger.info(f"[ScrcpyReader] H.264 内存解码器就绪")
        
        frame_count = 0
        decode_count = 0
        no_frame_count = 0
        last_reset_time = time.time()
        force_reset_interval = 300  # 5 分钟强制重置
        
        while self._running:
            try:
                # --- 读取帧元数据 ---
                meta = recv_exact(self._sock, FRAME_META_SIZE, timeout=1.0)
                if meta is None:
                    logger.warning(f"[ScrcpyReader] 连接断开 (meta=None)")
                    break
                
                # 解析 PTS + flags
                pts_bytes = meta[:8]
                pts = int.from_bytes(pts_bytes, 'big')
                is_config = bool(pts & CONFIG_FLAG)
                is_key = bool(pts & KEY_FLAG)
                pkt_size = int.from_bytes(meta[8:12], 'big')
                
                # 有效性检查
                if pkt_size <= 0 or pkt_size > 10 * 1024 * 1024:
                    logger.warning(f"[ScrcpyReader] 无效 pkt_size={pkt_size}")
                    continue
                
                # --- 读取帧数据 ---
                frame_data = recv_exact(self._sock, pkt_size, timeout=3.0)
                if frame_data is None or len(frame_data) < pkt_size:
                    logger.warning(f"[ScrcpyReader] 帧数据读取不完整")
                    continue
                
                frame_count += 1
                no_frame_count = 0  # 重置空帧计数器
                
                # --- CONFIG 帧处理（SPS/PPS，仅写入，不清除缓冲区） ---
                # 注意：scrcpy 协议中 SPS 帧可能早于 CONFIG_FLAG 帧到达
                # 因此不清除缓冲区，只追加数据
                if is_config:
                    logger.info(f"[ScrcpyReader] CONFIG 帧: {pkt_size}B")
                
                # 写入 H.264 数据
                self._decoder.write_data(frame_data)
                
                buf_size = len(self._decoder._buffer) if hasattr(self._decoder, '_buffer') else -1
                if frame_count <= 5 or frame_count % 100 == 0:
                    logger.info(f"[ScrcpyReader] Frame#{frame_count}: {pkt_size}B, config={is_config}, buf={buf_size}B")
                
                # --- 按间隔解码 ---
                if frame_count % self._decode_interval == 0:
                    jpeg = self._decoder.decode_latest()
                    if jpeg:
                        with self._lock:
                            self._latest_frame = jpeg
                            self._frame_seq += 1
                            self._frame_event.set()
                        decode_count += 1
                        if frame_count % 30 == 0 or decode_count <= 3:
                            logger.info(f"[ScrcpyReader] 解码成功! #{decode_count} (总帧 {frame_count}, JPEG={len(jpeg)}B)")
                    else:
                        if frame_count <= 8 or frame_count % 100 == 0:
                            logger.info(f"[ScrcpyReader] 解码失败 frame#{frame_count}")
                
                # --- 5分钟强制重置（但保留最近数据） ---
                if time.time() - last_reset_time > force_reset_interval:
                    logger.info(f"[ScrcpyReader] 强制重置解码器 (已运行 {force_reset_interval}s)")
                    self._decoder.trim(max_bytes=500_000)  # 保留最近 500KB
                    last_reset_time = time.time()
                
            except socket.timeout:
                # 正常超时，设备空闲时帧间隙可达 5-30s
                no_frame_count += 1
                
                # 长时间无帧 -> 可能连接断了，自动重启
                if no_frame_count > 6:  # 约 6s 无帧
                    logger.warning(f"[ScrcpyReader] 长时间无帧 ({no_frame_count*1.0:.0f}s)，触发自动恢复")
                    break
                continue
                
            except OSError as e:
                if not self._running:
                    break
                logger.warning(f"[ScrcpyReader] 读取错误: {e}")
                break
        
        logger.info(f"[ScrcpyReader] 后台线程退出，累计 {decode_count} 帧 (总 {frame_count} 帧)")
    
    async def get_frame(self, timeout: float = 5.0) -> Optional[bytes]:
        """
        获取最新 JPEG 帧
        
        阻塞等待直到有新帧可用或超时。
        
        Args:
            timeout: 等待超时（秒）
        
        Returns:
            JPEG bytes 或 None（超时/无帧）
        """
        if not self._running:
            return None
        
        # 清除旧事件
        self._frame_event.clear()
        
        # 检查是否有新帧
        with self._lock:
            if self._frame_seq > self._last_returned_seq:
                self._last_returned_seq = self._frame_seq
                return self._latest_frame
        
        # 等待新事件
        if self._frame_event.wait(timeout=timeout):
            with self._lock:
                self._last_returned_seq = self._frame_seq
                return self._latest_frame
        
        return None
    
    async def stop(self):
        """停止流，清理资源"""
        self._running = False
        
        # 关闭 socket
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        
        # 等待线程结束
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
            self._thread = None
        
        # 杀掉设备上的 scrcpy-server 进程
        subprocess.run(
            [self._adb_path, '-s', self._device_id, 'shell',
             'killall -9 app_process 2>/dev/null; echo done'],
            capture_output=True, timeout=3
        )
        
        # 杀掉 ADB 进程
        if self._proc:
            try:
                self._proc.kill()
                self._proc.wait(timeout=3)
            except Exception:
                pass
            self._proc = None
        
        # 清理 ADB forward
        subprocess.run(
            [self._adb_path, '-s', self._device_id, 'forward', '--remove',
             f'tcp:{self._local_port}'],
            capture_output=True, timeout=5
        )
        
        # 清理临时文件
        if self._decoder:
            self._decoder.cleanup()
            self._decoder = None
        
        # 清理帧缓存
        with self._lock:
            self._latest_frame = None
            self._frame_seq = 0
            self._last_returned_seq = 0
        
        logger.info(f"[ScrcpyReader] 设备 {self._device_id} 流已停止")


# ---- 快速测试入口 ----
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 测试配置（请根据实际环境修改）
    adb = r"D:\Android\QtScrcpy-win-x64-v3.3.3\adb.exe"
    device = "192.168.100.5:5555"
    server = r"D:\Android\QtScrcpy-win-x64-v3.3.3\scrcpy-server"
    
    async def test():
        reader = ScrcpyDeviceStreamReader(adb, device, server, max_size=720)
        if not await reader.start():
            print("❌ 启动失败")
            return
        
        print(f"✅ 启动成功: {reader.stream_info}")
        for i in range(10):
            frame = await reader.get_frame(3)
            if frame:
                print(f"  ✅ 帧 #{i+1}: {len(frame)} bytes (JPEG)")
            else:
                print(f"  ⏳ 帧 #{i+1}: 超时")
        
        await reader.stop()
        print("✅ 已停止")
    
    asyncio.run(test())
