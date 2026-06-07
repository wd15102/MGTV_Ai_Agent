# scrcpy-server 兼容性诊断总结

## 问题背景
MQTV 设备（Android 9, SDK 28, CM311-5-CH 机顶盒）的 WiFi ADB 截图速度慢，
遥控器操作后画面要 3~7 秒才能刷新。之前的 `screencap -p` 方案在 1080p 下每帧 ~3.3 秒。

## 探索路径

### 1. scrcpy-server H.264 硬件编码方案（失败）
- 下载了 scrcpy-server v3.2 和 v2.4 JAR
- `adb forward tcp:27183 localabstract:scrcpy` 成功
- 服务器启动正常（"Device: CM311-5-CH (Android 9)"）
- TCP 连接成功，但服务器仅发送 1 字节 (device name length = 0x00)
- **根因**：`app_process` 报错 `ClassNotFoundException`，JAR 中的 `classes.dex` 无法被
  该设备的 ART 运行时正确加载

```
tombstone: Didn't find class "com.genymobile.scrcpy.Server" on path: DexPathList[[],...]
```

- 尝试 v2.4 同样问题，尝试 `tunnel_forward=false` + `exec-out` 也失败（shell 嵌套问题）
- **结论**：该设备不支持 scrcpy-server 方案

### 2. 持久 ADB shell screencap 循环（方案切换）
- 改用 `adb shell "while true; do screencap -p; done"` 持久连接
- **1080p 全分辨率**：0.13 FPS（7.5 秒/帧），每帧 2.86 MB
- **720p 虚拟分辨率**：1.2 FPS（0.8 秒/帧），每帧 ~100 KB
- 优化幅度：**9x 帧率提升，28x 数据量下降**

### 3. 技术决策
`wm size 720x405` 临时降低虚拟分辨率，流结束后恢复原始分辨率。

## 已修改的文件
- `backend/app/stream/screen_stream.py` — 完整重写：
  - `DeviceStreamReader` 新增 `wm size` 管理
  - 改用 `adb shell "while true..."` 持久连接
  - 帧检测策略：IEND + PNG 头
  - 自动恢复原始分辨率
- ~backend/app/stream/optimized_stream.py~ 已删除（冗余）
