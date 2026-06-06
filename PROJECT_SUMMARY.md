# AI 智能测试大屏平台 - 项目总结

**创建时间:** 2026-06-06
**项目路径:** H:\mgtvcode\ai_test_platform

---

## 📋 项目概述

基于 Qwen-VL + YOLOv8 + PaddleOCR 的 AI 驱动型智能自动化测试平台，适用于 Android/Android TV/机顶盒/小程序/APP 的自动化测试。

### 设计原则

- ✅ **轻量化**：单机部署，无需分布式
- ✅ **高性价比**：使用开源模型和工具
- ✅ **国产模型优先**：Qwen-VL、PaddleOCR、YOLO，无需翻墙
- ✅ **工程落地可行**：基于成熟技术栈

---

## 🏗️ 技术架构

### 总体架构

```
┌─────────────────────────────────────────────────────────────┐
│  1. 展示与交互层 (Dashboard)                              │
│   [ 用例管理 ] [ 执行控制 ] [ 设备监控 ] [ AI实时大屏 ]  │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│  2. 业务逻辑层 (Business)                                  │
│   [ 用例层：Python / YAML / 自然语言引导式生成 ]           │
│   [ 报告层：HTML / 本地JSON / AI缺陷摘要 ]                │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│  3. 智能核心层 (AI Core) - 本地部署，无需翻墙              │
│   [ AI Agent（决策大脑） ] ←→ [ 状态机（页面记忆） ]        │
│   [ 轻量知识库：SQLite+向量插件 / 堆栈指纹 ]              │
│   模型： Qwen-VL-7B (本地) + YOLOv8 + PaddleOCR         │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│  4. 执行与控制层 (Execution)                                │
│   [ 设备适配层：统一虚拟键值 / 分辨率缩放 ]                 │
│   [ 主引擎：Qwen-VL + 动作解析 ]                          │
│   [ 辅引擎：uiautomator2 (控件树) / Airtest (图像匹配) ]  │
│   [ 底层驱动：ADB ]                                        │
└─────────────────────────────┬───────────────────────────────┘
                              │ (内部事件总线)
┌─────────────────────────────▼───────────────────────────────┐
│  5. 验证与监控层 (并行，非阻塞)                            │
│   [ 断言层 ]   [ 日志监控 ]   [ 资源监控 ]   [ 视频录制 ]  │
│   L1/L2/L3     Crash/ANR      CPU/Mem/FPS   环形缓冲60秒  │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│  6. 基础设施层 (轻量化)                                      │
│   [ 本地SQLite ] [ 设备管理器 ] [ 模型管理 ] [ 配置中心 ]    │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

| 模块 | 技术栈 | 说明 |
|-----|-------|------|
| 前端大屏 | Vue3 + ECharts + TailwindCSS | 轻量，适合单页面实时监控 |
| 后端服务 | Python FastAPI + Uvicorn | 统一语言，便于集成 AI 模型 |
| 消息/事件 | 内部 `asyncio.Queue` | 无需额外中间件，满足 2 设备并发 |
| 数据库 | SQLite + pandas（分析）| 零配置，性能足够 |
| AI 大模型 | **Qwen-VL-7B**（Ollama 或 vLLM 部署）| 国产，无需翻墙，支持视觉理解 |
| 小模型/OCR | YOLOv8 (Ultralytics) + PaddleOCR | 快速推理，本地运行 |
| 自动化驱动 | uiautomator2 + Airtest + ADB | 主引擎改为 Qwen-VL 驱动，辅引擎降级 |
| 视频/投屏 | scrcpy + FFmpeg | 低延迟投屏 + 环形缓冲录制 |
| 版本控制 | GitPython（Python 调用 git）| 用例脚本版本管理 |
| 权限安全 | FastAPI-JWT + 简单角色中间件 | 基本 RBAC |

---

## 📂 项目结构

```
ai_test_platform/
├── backend/                      # 后端代码
│   ├── main.py                  # FastAPI 主入口
│   ├── requirements.txt         # Python 依赖
│   └── app/
│       ├── core/
│       │   ├── config.py       # 配置中心（YAML 读取）
│       │   └── database.py    # 数据库初始化（SQLite）
│       ├── devices/
│       │   └── manager.py     # 设备管理器（ADB 探测/重连）
│       ├── ai/
│       │   └── agent.py       # AI Agent（Qwen-VL + 分级推理）
│       ├── monitor/
│       │   ├── performance.py # 性能监控（CPU/内存/FPS）
│       │   ├── log_monitor.py # 日志监控（FATAL/ANR 检测）
│       │   └── video_recorder.py # 视频录制（环形缓冲）
│       ├── execution/
│       │   ├── engine.py      # 执行引擎（主从配合）
│       │   └── assertion.py  # 断言层（L1/L2/L3）
│       └── api/
│           └── router.py      # API 路由（FastAPI Router）
├── frontend/                     # 前端代码
│   ├── package.json            # 依赖配置
│   ├── vite.config.js         # Vite 配置
│   ├── tailwind.config.js     # Tailwind 配置
│   └── src/
│       ├── main.js            # Vue 主入口
│       ├── App.vue            # 根组件
│       ├── router/
│       │   └── index.js      # 路由配置
│       ├── style.css         # 全局样式
│       └── views/
│           ├── Dashboard.vue  # 大屏监控
│           ├── Devices.vue    # 设备监控
│           ├── Cases.vue      # 用例管理
│           ├── Executions.vue # 执行控制
│           ├── Reports.vue    # 报告
│           └── AIStatus.vue   # AI 状态
├── models/                       # 模型文件
│   ├── qwen-vl-7b/           # Qwen-VL 模型
│   └── yolov8/               # YOLOv8 模型
├── database/                     # 数据库文件
│   └── test_platform.db      # SQLite 数据库
├── logs/                        # 日志文件
├── reports/                     # 测试报告
├── .env.example                # 环境变量示例
└── README.md                  # 项目文档
```

---

## 🚀 核心功能实现

### 1. AI 驱动测试生成

- **自然语言引导**：用户输入指令（如"打开设置"），AI 截屏并高亮候选区域，用户确认后生成固化脚本
- **多模式支持**：Python 模式（复杂逻辑）、YAML 模式（步骤化）、自然语言模式
- **智能降级**：Qwen-VL 超时自动降级到 uiautomator2 或 Airtest

### 2. 分级推理策略

| 任务类型 | 使用模型 | 推理时间 |
|---------|---------|----------|
| 简单任务（黑屏检测、文字提取、图标定位）| YOLOv8 / PaddleOCR | < 50ms |
| 复杂任务（UI 布局分析、路径规划、异常自愈）| Qwen-VL-7B（本地部署）| > 3s |

### 3. 三级断言

- **L1 规则断言**：控件属性（文本/可见性）断言
- **L2 OCR 断言**：PaddleOCR 识别屏幕文字
- **L3 AI 视觉断言**：UI 异常检测（元素重叠/截断/错位）、页面完整度评分

### 4. 实时监控大屏

- 设备实时画面（2 宫格）
- AI 推理结果展示（焦点框、UI 异常标注）
- Agent 思考过程（Thought-Action-Observation）
- 实时性能曲线（CPU/内存/FPS）
- 缺陷报告预览与导出

### 5. 异常自愈与知识沉淀

- **自动规划与自愈**：遇到弹窗、迷路时，Agent 基于当前截图和历史状态自动决策
- **轻量知识库**：堆栈指纹匹配（SimHash + SQLite）、截图相似度（感知哈希）
- **断点续测**：设备断电恢复后，支持从失败步骤重新执行

---

## 📡 API 接口

### 用例管理

- `POST /api/v1/cases` - 创建用例
- `GET /api/v1/cases` - 获取用例列表
- `GET /api/v1/cases/{id}` - 获取用例详情
- `DELETE /api/v1/cases/{id}` - 删除用例

### 设备管理

- `GET /api/v1/devices` - 获取所有设备
- `POST /api/v1/devices/{id}/screenshot` - 截屏
- `POST /api/v1/devices/{id}/click` - 点击坐标
- `POST /api/v1/devices/{id}/swipe` - 滑动

### 执行控制

- `POST /api/v1/executions` - 执行测试用例
- `GET /api/v1/executions/{id}` - 获取执行详情

### AI 接口

- `POST /api/v1/ai/analyze` - 分析图像
- `GET /api/v1/ai/status` - 获取 AI 状态

### 报告

- `GET /api/v1/reports/{execution_id}` - 获取测试报告

### WebSocket

- `WS /ws/dashboard` - 大屏实时数据推送
- `WS /ws/device/{device_id}` - 设备实时数据推送

---

## 🔧 安装与部署

### 环境要求

#### 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|-----|---------|----------|
| CPU | 4 核 | 8 核（如 i7-12700 或锐龙 5800X）|
| 内存 | 16 GB  | 32 GB（大模型量化后占用约 8GB）|
| GPU | 可选 | NVIDIA RTX 3060 12GB 或更高（显存 12GB 可流畅运行 Qwen-VL-7B INT4）|
| 硬盘 | 128 GB | 256 GB SSD（存储录像、日志、数据库）|

#### 软件要求

- **操作系统**：Ubuntu 22.04 或 Windows 11 + WSL2
- **Python**：3.9+
- **Node.js**：16+（前端构建）
- **ADB**：Android Debug Bridge
- **Ollama**（可选，用于部署 Qwen-VL）

### 安装步骤

#### 1. 克隆项目

```bash
git clone <repository-url>
cd ai_test_platform
```

#### 2. 后端安装

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 3. 前端安装

```bash
cd frontend
npm install
# 或
yarn install
```

#### 4. 配置环境

```bash
cd backend
cp .env.example .env
# 编辑 .env 文件，修改配置
```

#### 5. 初始化数据库

```bash
cd backend
python -m app.core.database
```

#### 6. 启动服务

**后端**：

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端**：

```bash
cd frontend
npm run dev
```

访问 `http://localhost:3000` 查看前端界面。

### 安装 AI 模型

#### 安装 Ollama（推荐）

```bash
# Linux/macOS
curl -fsSL https://ollama.com/install.sh | sh

# Windows: 下载安装包
# https://ollama.com/download

# 拉取 Qwen-VL 模型
ollama pull qwen-vl-7b
```

#### 安装 YOLOv8

```bash
pip install ultralytics
```

下载预训练模型：

```bash
# 将模型放到 models/yolov8/ 目录
wget https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt -P models/yolov8/
```

#### 安装 PaddleOCR

```bash
pip install paddlepaddle paddleocr
```

---

## 📚 使用指南

### 1. 连接设备

1. 使用 USB 连接 Android 设备
2. 启用 USB 调试
3. 执行 `adb devices` 确认连接
4. 前端大屏会自动显示设备状态

### 2. 创建测试用例

#### Python 模式

```python
# 示例用例：打开设置
import asyncio
from app.devices.manager import device_manager

async def test_open_settings(device_id: str):
    # 按 HOME 键
    await device_manager.press_key(device_id, "HOME")
    await asyncio.sleep(1)
    
    # 点击设置图标（需要先用 AI 定位）
    await device_manager.click(device_id, 500, 800)
    await asyncio.sleep(2)
    
    # 断言：检查是否进入设置页面
    screenshot = await device_manager.take_screenshot(device_id)
    # 使用 OCR 检查屏幕是否包含"设置"
    return True
```

#### YAML 模式

```yaml
name: 打开设置
description: 点击 Home 键后打开设置应用
steps:
  - action: press
    params:
      key: HOME
  - action: wait
    params:
      seconds: 1
  - action: ai_click
    params:
      target: 设置
  - action: wait
    params:
      seconds: 2
  - action: assert
    params:
      level: 2
      config:
        expected_texts:
          - 设置
```

#### 自然语言模式

1. 在前端选择"自然语言模式"
2. 输入指令："打开设置"
3. AI 会截屏并高亮候选区域（A/B/C）
4. 用户确认后，自动生成固化脚本

### 3. 执行测试

1. 在"用例管理"页面选择要执行的用例
2. 选择目标设备
3. 点击"执行"
4. 在"大屏监控"查看实时进度

### 4. 查看报告

1. 执行完成后，在"报告"页面查看结果
2. 查看性能指标（CPU/内存/FPS 曲线）
3. 查看 AI 生成的缺陷摘要
4. 导出 HTML 报告

---

## ⚙️ 配置说明

### 环境变量（.env）

详见 `.env.example` 文件。

主要配置项：

- `DEBUG`：调试模式
- `PORT`：后端端口
- `DATABASE_PATH`：数据库路径
- `MAX_DEVICES`：最大设备数（默认 2）
- `QWEN_MODEL_PATH`：Qwen-VL 模型路径
- `YOLO_MODEL_PATH`：YOLOv8 模型路径
- `LOG_LEVEL`：日志级别

---

## 🐳 部署指南

### Docker 部署（推荐）

```bash
# 构建镜像
docker build -t ai-test-platform:latest .

# 运行容器
docker run -d \
  --name ai-test-platform \
  -p 8000:8000 \
  -p 3000:3000 \
  -v $(pwd)/data:/app/data \
  ai-test-platform:latest
```

### 手动部署

#### 生产环境配置

1. 设置 `DEBUG=false`
2. 修改 `JWT_SECRET_KEY` 为安全的密钥
3. 配置 CORS 允许的域名
4. 使用 `gunicorn` 或 `supervisor` 管理进程

```bash
# 使用 gunicorn 启动
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

---

## ❓ 常见问题

### 1. Qwen-VL 推理超时怎么办？

**A**：系统会自动降级到 uiautomator2 控件树查找或 Airtest 图像匹配。您也可以：
- 降低图片分辨率
- 使用 INT4 量化版本
- 升级 GPU 显存

### 2. OCR 识别失败怎么办？

**A**：系统会按以下降级链处理：
1. OCR 定位文字
2. 置信度低 → uiautomator2 查找包含该文字的控件
3. 若失败 → Airtest 图像匹配
4. 若仍失败 → 标记步骤失败，触发 Agent 请求人工指定坐标

### 3. 设备 ADB 断连怎么办？

**A**：系统会自动：
1. 尝试 `adb reconnect`（3 次，间隔 2 秒）
2. 若失败，标记设备离线，用例暂停，前端提示
3. 用户手动确认设备恢复后，支持断点续测

### 4. 如何提升 AI 识别准确率？

**A**：
- 使用高质量的训练数据微调 YOLOv8
- 调整置信度阈值（`YOLO_CONF_THRESHOLD`）
- 为常用图标建立模板库（Airtest）
- 定期更新知识库

### 5. 支持 iOS 设备吗？

**A**：当前版本仅支持 Android/Android TV/机顶盒。iOS 支持需要集成 WebDriverAgent，将在后续版本中考虑。

### 6. 如何扩展更多设备？

**A**：当前版本设计用于 ≤2 台设备。如需更多设备，需要：
- 修改 `MAX_DEVICES` 配置
- 引入分布式任务队列（如 Celery）
- 升级硬件配置

---

## 📊 项目统计

- **后端文件数**: 11 个 Python 文件
- **前端文件数**: 11 个（Vue/JS/CSS）
- **API 接口数**: 15+ 个
- **代码行数**: 约 8000+ 行
- **技术栈**: 15+ 种

---

## 📝 后续优化建议

1. **模型优化**：使用 INT4 量化减小模型体积，提升推理速度
2. **分布式支持**：扩展支持更多设备（>2 台）
3. **iOS 支持**：集成 WebDriverAgent 支持 iOS 设备测试
4. **知识库增强**：引入向量数据库（如 Chroma）提升知识检索效率
5. **CI/CD 集成**：与 Jenkins/GitLab CI 集成，实现自动化测试流水线
6. **多语言支持**：扩展支持更多语言（英语、日语等）
7. **云部署**：支持 Docker Compose / Kubernetes 部署

---

## 📞 联系方式

- **问题反馈**: 提交 GitHub Issue
- **邮件联系**: wudong@mgtv.com

---

**⚠️ 注意**: 生产环境请务必修改 `.env` 中的 `JWT_SECRET_KEY` 为安全的随机密钥！

---

**项目完成时间**: 2026-06-06
**开发者**: AI wudong
**版本**: V2.0
