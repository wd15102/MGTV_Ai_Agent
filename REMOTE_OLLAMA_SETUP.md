# 远程 Ollama 部署方案 - 完整配置指南

## 📋 方案概述

本方案使用 **Tailscale VPN** 实现家里电脑（Ollama 服务）与公司电脑（客户端）的安全远程访问。

---

## 🖥️ 一、家里电脑（服务端）配置

### 1. 安装 Tailscale

#### 方法1：命令行安装（推荐）
```powershell
# 下载 Tailscale
$url = "https://pkgs.tailscale.com/stable/tailscale-setup.exe"
$output = "$env:TEMP\tailscale-setup.exe"
Invoke-WebRequest -Uri $url -OutFile $output

# 静默安装
Start-Process $output -ArgumentList "/quiet" -Wait
```

#### 方法2：手动下载
访问：https://tailscale.com/download/windows
下载并安装

---

### 2. 启动 Tailscale 并登录

```powershell
# 启动 Tailscale（会弹出浏览器登录）
tailscale up

# 获取 Tailscale IP（记下这个 IP，例如：100.71.173.9）
tailscale ip -4
```

**输出示例：**
```
100.71.173.9
```

---

### 3. 配置 Ollama 允许远程访问

#### 临时设置（重启后失效）
```powershell
# 设置 Ollama 监听所有网卡
$env:OLLAMA_HOST = "0.0.0.0:11434"

# 启动 Ollama
ollama serve
```

#### 永久设置（推荐）
```powershell
# 设置用户环境变量（重启后生效）
[System.Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0:11434", "User")

# 验证设置
Get-ChildItem Env: | Where-Object Name -eq "OLLAMA_HOST"
```

---

### 4. 下载 AI 模型

```powershell
# 新开一个 PowerShell 窗口

# 下载 Qwen2.5-7B（推荐，中文支持好）
ollama pull qwen2.5:7b

# 下载 DeepSeek-R1-8B（推理能力强）
ollama pull deepseek-r1:8b

# 下载 Gemma3-4B（轻量，速度快）
ollama pull gemma3:4b

# 查看已安装的模型
ollama list
```

---

### 5. 验证 Ollama 服务

```powershell
# 测试 API 是否可访问
curl http://localhost:11434/api/tags

# 测试模型推理
ollama run qwen2.5:7b "你好，请介绍一下自己"
```

**预期输出：**
```json
{
  "models": [
    {
      "name": "qwen2.5:7b",
      "model": "qwen2.5:7b",
      ...
    }
  ]
}
```

---

## 💻 二、公司电脑（客户端）配置

### 1. 安装 Tailscale

（同家里电脑步骤1）

---

### 2. 启动 Tailscale 并登录

```powershell
# 启动 Tailscale（使用同一个账号登录）
tailscale up

# 验证是否能访问家里电脑
ping 100.71.173.9  # 替换成家里电脑的 Tailscale IP
```

---

### 3. 测试远程 Ollama API

```powershell
# 测试连接
curl http://100.71.173.9:11434/api/tags

# 预期输出：
# {
#   "models": [
#     {"name": "qwen2.5:7b", ...},
#     {"name": "deepseek-r1:8b", ...}
#   ]
# }
```

---

### 4. 配置项目代码

#### 方法1：修改 `.env` 文件（推荐）

创建/编辑 `D:\WorkCode\AiTest\MGTV_Ai_Agent\backend\.env`：

```env
# Ollama 远程访问配置
OLLAMA_BASE_URL=http://100.71.173.9:11434
OLLAMA_MODEL=qwen2.5:7b

# JWT Secret Key（生产环境必须修改！）
JWT_SECRET_KEY=dev-secret-key-change-in-production-only-2026

# 调试模式
DEBUG=True

# 数据库路径
DATABASE_PATH=../../database/test_platform.db
```

---

#### 方法2：直接修改 `config.py`

编辑 `D:\WorkCode\AiTest\MGTV_Ai_Agent\backend\app\core\config.py`：

```python
class Settings(BaseSettings):
    # ... 其他配置 ...
    
    # Ollama 配置（远程访问）
    QWEN_OLLAMA_BASE_URL: str = "http://100.71.173.9:11434"  # Tailscale IP
    QWEN_OLLAMA_MODEL: str = "qwen2.5:7b"
    QWEN_INFERENCE_TIMEOUT: int = 30  # 远程访问需要更长超时
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

---

### 5. 验证项目代码

#### 检查 `agent.py` 配置

确认 `D:\WorkCode\AiTest\MGTV_Ai_Agent\backend\app\ai\agent.py` 包含：

```python
from app.core.config import settings

class AIAgent:
    def __init__(self):
        # 从配置读取 Ollama URL
        self.qwen_base_url = settings.QWEN_OLLAMA_BASE_URL
        self.qwen_model = settings.QWEN_OLLAMA_MODEL
        self.qwen_timeout = settings.QWEN_INFERENCE_TIMEOUT
        # ...
```

---

## 🚀 三、启动项目并测试

### 1. 启动后端服务

```powershell
# 激活虚拟环境
& "D:\WorkCode\AiTest\MGTV_Ai_Agent\.venv\Scripts\Activate.ps1"

# 进入 backend 目录
cd D:\WorkCode\AiTest\MGTV_Ai_Agent\backend

# 启动服务
python main.py
```

**预期输出：**
```
INFO: Started server process [12345]
INFO: Uvicorn running on http://0.0.0.0:8000
INFO: ✅ Qwen 模型可用: qwen2.5:7b
```

---

### 2. 测试 API 端点

#### 测试设备连接
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/devices" -Method Get
```

#### 测试 AI 分析功能
```powershell
# 先准备一张测试截图，例如：D:\test_screenshot.png

$body = @{
    "image_path" = "D:\test_screenshot.png"
    "task" = "识别屏幕上的所有文字"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/ai/analyze" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
```

---

### 3. 访问 Web UI

打开浏览器，访问：
```
http://localhost:8000/docs
```

这是 FastAPI 自动生成的 API 文档，可以在这里测试所有接口。

---

## 🔧 四、常见问题与调试

### 问题1：Tailscale 无法连接

**症状：**
```
ping 100.71.173.9
请求超时。
```

**解决方案：**
1. 检查两台电脑是否登录了**同一个 Tailscale 账号**
2. 检查防火墙是否阻止了 Tailscale：
   ```powershell
   # 允许 Tailscale 通过防火墙
   New-NetFirewallRule -DisplayName "Tailscale" -Direction Inbound -Program "C:\Program Files\Tailscale\tailscale.exe" -Action Allow
   ```
3. 重启 Tailscale 服务：
   ```powershell
   Restart-Service Tailscale
   ```

---

### 问题2：Ollama 远程访问失败

**症状：**
```
curl http://100.71.173.9:11434/api/tags
curl: (7) Failed to connect to 100.71.173.9 port 11434 after 1000ms
```

**解决方案：**
1. 检查家里电脑的 Ollama 是否设置了 `OLLAMA_HOST`：
   ```powershell
   # 在服务器上运行
   Get-ChildItem Env: | Where-Object Name -eq "OLLAMA_HOST"
   ```
   
2. 检查 Ollama 是否正在运行：
   ```powershell
   Get-Process ollama
   ```
   
3. 检查端口是否监听：
   ```powershell
   netstat -an | Select-String "11434"
   ```

---

### 问题3：项目启动后 AI 分析失败

**症状：**
```
ERROR: Qwen 调用失败: 500
```

**解决方案：**
1. 检查 `agent.py` 中的 `qwen_timeout` 是否太短（远程访问需要更长超时）：
   ```python
   self.qwen_timeout = 30  # 改成 30 秒
   ```
   
2. 检查模型名称是否正确：
   ```powershell
   # 在家里电脑上运行
   ollama list
   
   # 确认输出的模型名称与配置文件一致
   # 例如：qwen2.5:7b（不是 qwen-vl-7b）
   ```

---

### 问题4：GPU 未加速

**症状：**
- 推理速度很慢（< 5 tokens/秒）
- 任务管理器中 GPU 利用率为 0%

**解决方案：**
1. 检查 Ollama 是否识别到 GPU：
   ```powershell
   ollama show qwen2.5:7b
   
   # 查看输出中是否有 "gpu_layers"
   ```
   
2. 如果有 NVIDIA GPU 但未使用，重新安装 CUDA 驱动：
   - 下载地址：https://developer.nvidia.com/cuda-toolkit

---

## 📊 五、性能优化建议

### 1. 家里电脑（服务端）

#### 设置模型存储路径（避免 C 盘空间不足）
```powershell
# 设置环境变量
[System.Environment]::SetEnvironmentVariable("OLLAMA_MODELS", "D:\OllamaModels", "User")

# 重启 Ollama
Restart-Service Ollama  # 如果安装为服务
# 或者手动重启 ollama serve
```

#### 启用 GPU 加速
```powershell
# 检查 GPU 是否被识别
ollama show qwen2.5:7b

# 如果输出中有 "gpu_layers": 0，说明未启用 GPU
# 需要安装 NVIDIA CUDA 驱动
```

---

### 2. 公司电脑（客户端）

#### 增加超时时间（防止公司网络慢导致超时）
编辑 `agent.py`：
```python
class AIAgent:
    def __init__(self):
        # ...
        self.qwen_timeout = 30  # 改成 30 秒（默认 5 秒太短）
```

---

## 🔒 六、安全建议

### 1. 使用 Tailscale ACL（访问控制列表）

编辑 Tailscale 控制面板：https://login.tailscale.com/admin/acls

示例 ACL：
```json
{
  "acls": [
    {
      "action": "accept",
      "users": ["your-email@example.com"],
      "ports": ["100.71.173.9:11434"]
    }
  ]
}
```

---

### 2. 限制 Ollama 访问来源 IP

在家里电脑上设置防火墙规则：
```powershell
# 只允许 Tailscale 网段访问 Ollama
New-NetFirewallRule -DisplayName "Ollama - Tailscale Only" `
    -Direction Inbound `
    -LocalPort 11434 `
    -Protocol TCP `
    -RemoteAddress 100.64.0.0/10 `
    -Action Allow
```

---

## 📋 七、完整配置检查清单

### ✅ 家里电脑（服务端）
- [ ] 安装 Tailscale 并登录
- [ ] 设置 `OLLAMA_HOST=0.0.0.0:11434`
- [ ] 启动 Ollama 服务（`ollama serve`）
- [ ] 下载模型（`ollama pull qwen2.5:7b`）
- [ ] 验证 API 可访问（`curl http://localhost:11434/api/tags`）
- [ ] 记录 Tailscale IP（`tailscale ip -4`）

### ✅ 公司电脑（客户端）
- [ ] 安装 Tailscale 并登录（同一个账号）
- [ ] 测试连接（`ping <家里电脑 Tailscale IP>`）
- [ ] 测试远程 API（`curl http://<Tailscale IP>:11434/api/tags`）
- [ ] 配置 `.env` 文件（`OLLAMA_BASE_URL=http://<Tailscale IP>:11434`）
- [ ] 启动项目（`python main.py`）
- [ ] 测试 AI 分析功能

---

## 📞 技术支持

如果遇到问题，请提供以下信息：
1. 家里电脑的 Tailscale IP
2. 公司电脑的 Tailscale IP
3. `curl http://<Tailscale IP>:11434/api/tags` 的输出
4. 项目日志（`logs/platform.log`）

---

**最后更新：2026-06-06**
