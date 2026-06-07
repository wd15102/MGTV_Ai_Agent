# 屏幕流模块状态

## 当前状态：✅ 已集成并通过端到端测试

### 架构

```
┌──────────┐     H.264 HW Enc     ┌──────────────────┐     JPEG (WebSocket)    ┌──────────┐
│  CM311-5  │ ◄──── ADB forward ──► │  ScrcpyDevice    │ ◄──────────────────────► │  前端     │
│ (Android9)│    scrcpy-server     │  StreamReader     │     localhost:8090       │  Vue SPA  │
└──────────┘                      └───────┬──────────┘                          └──────────┘
                                          │ OpenCV decode + JPEG encode
                                          ▼
                                    ┌──────────┐
                                    │  H264FrameDecoder  │
                                    └──────────┘
```

### 文件清单

| 文件 | 说明 |
|------|------|
| `screen_stream.py` | WebSocket 流管线（ScrcpyScreenStreamer 推送 JPEG 帧） |
| `screen_stream_png.py` | 降级方案（PNG 截图轮询，~1.2 FPS） |
| `scrcpy_reader.py` | H.264 流读取器 + NAL 解码器 |
| `test_scrcpy_reader.py` | scrcpy_reader 单元测试 |
| `test_scrcpy_long.py` | 长周期压力测试 |
| `test_ws_integration.py` | 端到端 WebSocket 测试 |

### 性能数据

- **H.264 方案**（当前）：720p × 408p @ 2Mbps，~15 FPS 编码
- **PNG 降级方案**：720p，~1.2 FPS（WiFi 瓶颈）
- **每帧大小**：~40 KB JPEG → WebSocket
- **设备空闲时**：编码器休眠，帧间隙 5-30 秒（正常行为）

### 待改进

1. **帧缓存清理**：`get_frame()` 可能返回重复帧（需加帧序号检测）
2. **自动重连**：线程因 socket 超时退出后需重建连接
3. **多设备支持**：当前单例 ScrcpyScreenStreamer 只支持 1 台设备
4. **前端适配**：Vue SPA 需要连接 WebSocket 并渲染 JPEG 帧

### 后端地址

```
API:      http://localhost:8090/api/status
Docs:     http://localhost:8090/docs
WebSocket ws://localhost:8090/ws/device/{device_id}/screen
```

### 启动命令

```bash
cd D:\WorkCode\AiTest\MGTV_Ai_Agent\backend
python -m uvicorn main:app --host 0.0.0.0 --port 8090
```
