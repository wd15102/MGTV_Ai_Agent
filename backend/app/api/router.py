"""
API 路由 - 统一接口
提供 RESTful API 供前端调用
"""
import asyncio
import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


# ==================== 请求模型 ====================

class CreateCaseRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    type: str = "python"
    content: str
    version: Optional[str] = None


class ExecuteCaseRequest(BaseModel):
    case_id: int
    device_id: str


class DeviceActionRequest(BaseModel):
    action: str
    params: Optional[Dict] = None


class AIQueryRequest(BaseModel):
    image_path: str
    task: str
    confidence_threshold: Optional[float] = 0.85


class KeyEventRequest(BaseModel):
    keycode: str


class KeyEventCoordinates(BaseModel):
    x: int
    y: int


# ==================== 用例管理 ====================

@router.post("/cases", tags=["用例管理"])
async def create_case(request: CreateCaseRequest):
    """创建测试用例"""
    try:
        from app.core.database import execute_query, fetch_one

        cursor = await execute_query("""
            INSERT INTO test_cases (name, description, type, content, version, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            request.name,
            request.description,
            request.type,
            request.content,
            request.version,
            "admin"
        ))

        case = await fetch_one("SELECT last_insert_rowid() as id")
        case_id = case["id"]

        return {
            "success": True,
            "case_id": case_id,
            "message": "用例创建成功"
        }

    except Exception as e:
        logger.error(f"创建用例失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cases", tags=["用例管理"])
async def list_cases(
    page: int = 1,
    page_size: int = 20,
    type: Optional[str] = None
):
    """获取用例列表"""
    try:
        from app.core.database import fetch_all, fetch_one

        query = "SELECT * FROM test_cases WHERE 1=1"
        params = []

        if type:
            query += " AND type = ?"
            params.append(type)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([page_size, (page - 1) * page_size])

        rows = await fetch_all(query, tuple(params))
        cases = [dict(row) for row in rows]

        count_query = "SELECT COUNT(*) as total FROM test_cases"
        count_row = await fetch_one(count_query)
        total = count_row["total"]

        return {
            "success": True,
            "data": cases,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total
            }
        }

    except Exception as e:
        logger.error(f"获取用例列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cases/{case_id}", tags=["用例管理"])
async def get_case(case_id: int):
    """获取用例详情"""
    try:
        from app.core.database import fetch_one

        row = await fetch_one("SELECT * FROM test_cases WHERE id = ?", (case_id,))

        if not row:
            raise HTTPException(status_code=404, detail="用例不存在")

        return {
            "success": True,
            "data": dict(row)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用例详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cases/{case_id}", tags=["用例管理"])
async def delete_case(case_id: int):
    """删除用例"""
    try:
        from app.core.database import execute_query, fetch_one

        row = await fetch_one("SELECT id FROM test_cases WHERE id = ?", (case_id,))
        if not row:
            raise HTTPException(status_code=404, detail="用例不存在")

        await execute_query("DELETE FROM test_cases WHERE id = ?", (case_id,))

        return {
            "success": True,
            "message": "用例删除成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除用例失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 设备管理 ====================

@router.get("/devices", tags=["设备管理"])
async def list_devices():
    """获取所有设备"""
    try:
        from main import device_manager
        devices = await device_manager.get_status()
        return {"success": True, "data": devices}
    except Exception as e:
        logger.error(f"获取设备列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/devices/{device_id}/screenshot", tags=["设备管理"])
async def take_screenshot(device_id: str):
    """截屏"""
    try:
        from main import device_manager

        path = await device_manager.take_screenshot(device_id)

        if not path:
            raise HTTPException(status_code=500, detail="截屏失败")

        from pathlib import Path as _Path
        # 截图存储在项目根目录的 logs/screenshots/{device_id_safe}/{timestamp}.png
        path_obj = _Path(path)
        if path_obj.name:  # 返回文件名即可，前端通过 base64/stream 获取图片
            return {"success": True, "path": path_obj.name}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"截屏失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/devices/{device_id}/screenshot/stream", tags=["设备管理"])
async def stream_screenshot(device_id: str):
    """
    快速截屏流接口（每次调用获取最新截图）
    返回 base64 编码的 PNG 图片数据，前端可直接用于 img.src
    """
    try:
        import base64
        from main import device_manager

        path = await device_manager.take_screenshot(device_id)

        if not path:
            raise HTTPException(status_code=500, detail="截屏失败")

        from pathlib import Path as _Path
        img_path = _Path(path)
        if not img_path.exists():
            raise HTTPException(status_code=500, detail="截图文件不存在")

        with open(img_path, "rb") as f:
            img_data = f.read()

        b64_data = base64.b64encode(img_data).decode("utf-8")

        return {
            "success": True,
            "path": img_path.name,
            "base64": f"data:image/png;base64,{b64_data}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"截屏流接口失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/devices/{device_id}/click", tags=["设备管理"])
async def click_device(device_id: str, x: int, y: int):
    """点击坐标"""
    try:
        from main import device_manager
        success = await device_manager.click(device_id, x, y)
        return {
            "success": success,
            "message": "点击成功" if success else "点击失败"
        }
    except Exception as e:
        logger.error(f"点击失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/devices/{device_id}/swipe", tags=["设备管理"])
async def swipe_device(
    device_id: str,
    x1: int, y1: int,
    x2: int, y2: int,
    duration: int = 300
):
    """滑动"""
    try:
        from main import device_manager
        success = await device_manager.swipe(device_id, x1, y1, x2, y2, duration)
        return {
            "success": success,
            "message": "滑动成功" if success else "滑动失败"
        }
    except Exception as e:
        logger.error(f"滑动失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 设备遥控器 (KeyEvent) ====================

@router.post("/devices/{device_id}/keyevent", tags=["设备管理"])
async def press_key(device_id: str, request: KeyEventRequest):
    """
    发送按键事件到设备
    keycode 支持数字键值及命名键值: HOME, BACK, MENU, UP, DOWN, LEFT, RIGHT, ENTER, OK
    VOLUME_UP, VOLUME_DOWN, POWER, PLAY, PAUSE, STOP 等
    """
    try:
        from main import device_manager

        named_keys = {
            "HOME": "3", "BACK": "4", "CALL": "5", "ENDCALL": "6",
            "UP": "19", "DOWN": "20", "LEFT": "21", "RIGHT": "22",
            "ENTER": "23", "OK": "23", "DPAD_UP": "19", "DPAD_DOWN": "20",
            "DPAD_LEFT": "21", "DPAD_RIGHT": "22", "DPAD_CENTER": "23",
            "VOLUME_UP": "24", "VOLUME_DOWN": "25", "POWER": "26",
            "CAMERA": "27", "CLEAR": "28", "MENU": "82", "NOTIFICATION": "83",
            "SEARCH": "84", "PLAY": "126", "PAUSE": "127", "STOP": "128",
            "NEXT": "87", "PREVIOUS": "88", "REWIND": "89", "FAST_FORWARD": "90",
            "NUM_0": "7", "NUM_1": "8", "NUM_2": "9", "NUM_3": "10",
            "NUM_4": "11", "NUM_5": "12", "NUM_6": "13", "NUM_7": "14",
            "NUM_8": "15", "NUM_9": "16",
            "SETTINGS": "176", "TV": "170", "GUIDE": "172", "INFO": "165",
            "SOURCE": "178", "SUBTITLE": "184", "CAPTION": "184",
            "MUTE": "91", "MEDIA_PLAY_PAUSE": "85",
        }

        keycode_str = request.keycode.strip()

        if keycode_str.upper() in named_keys:
            keycode_str = named_keys[keycode_str.upper()]

        success = await device_manager.press_key(device_id, keycode_str)

        if success:
            logger.info(f"📡 设备 {device_id} 发送按键: {request.keycode} (keycode={keycode_str})")

        return {
            "success": success,
            "message": f"按键 {request.keycode} 发送成功" if success else f"按键 {request.keycode} 发送失败",
            "keycode": keycode_str
        }

    except Exception as e:
        logger.error(f"按键失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 执行控制 ====================

@router.post("/executions", tags=["执行控制"])
async def execute_case(request: ExecuteCaseRequest):
    """执行测试用例"""
    try:
        from app.core.database import execute_query, fetch_one
        from app.execution.engine import ExecutionEngine
        from main import device_manager
        from app.ai.agent import AIAgent

        cursor = await execute_query("""
            INSERT INTO executions (case_id, device_id, status, start_time)
            VALUES (?, (SELECT id FROM devices WHERE device_id = ?), ?, ?)
        """, (
            request.case_id,
            request.device_id,
            "running",
            datetime.now().isoformat()
        ))

        exec_row = await fetch_one("SELECT last_insert_rowid() as id")
        execution_id = exec_row["id"]

        async def run():
            engine = ExecutionEngine(device_manager, AIAgent())
            result = await engine.execute_case(
                request.case_id,
                request.device_id,
                execution_id
            )
            logger.info(f"执行完成: {result}")

        asyncio.create_task(run())

        return {
            "success": True,
            "execution_id": execution_id,
            "message": "执行已开始"
        }

    except Exception as e:
        logger.error(f"执行用例失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/{execution_id}", tags=["执行控制"])
async def get_execution(execution_id: int):
    """获取执行详情"""
    try:
        from app.core.database import fetch_one

        row = await fetch_one("SELECT * FROM executions WHERE id = ?", (execution_id,))

        if not row:
            raise HTTPException(status_code=404, detail="执行记录不存在")

        return {
            "success": True,
            "data": dict(row)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取执行详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AI 接口 ====================

@router.post("/ai/analyze", tags=["AI 接口"])
async def analyze_image(request: AIQueryRequest):
    """分析图像"""
    try:
        from app.ai.agent import AIAgent

        agent = AIAgent()
        result = await agent.analyze_image(
            request.image_path,
            request.task,
            request.confidence_threshold
        )

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"分析图像失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai/status", tags=["AI 接口"])
async def get_ai_status():
    """获取 AI 状态"""
    try:
        from app.ai.agent import AIAgent

        agent = AIAgent()
        status = agent.get_status()

        return {
            "success": True,
            "data": status
        }

    except Exception as e:
        logger.error(f"获取 AI 状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 报告 ====================

@router.get("/reports/{execution_id}", tags=["报告"])
async def get_report(execution_id: int):
    """获取测试报告"""
    try:
        from app.core.database import fetch_one, fetch_all

        exec_row = await fetch_one("SELECT * FROM executions WHERE id = ?", (execution_id,))
        if not exec_row:
            raise HTTPException(status_code=404, detail="执行记录不存在")

        perf_rows = await fetch_all(
            "SELECT * FROM performance_data WHERE execution_id = ? ORDER BY timestamp",
            (execution_id,)
        )

        log_rows = await fetch_all(
            "SELECT * FROM logs WHERE execution_id = ? ORDER BY timestamp",
            (execution_id,)
        )

        return {
            "success": True,
            "data": {
                "execution": dict(exec_row),
                "performance": [dict(row) for row in perf_rows],
                "logs": [dict(row) for row in log_rows]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== WebSocket ====================

@router.websocket("/ws/device/{device_id}")
async def websocket_device(websocket: WebSocket, device_id: str):
    """设备实时数据 WebSocket"""
    await websocket.accept()
    try:
        while True:
            from main import device_manager
            from app.monitor.performance import PerformanceMonitor

            data = {
                "device": await device_manager.get_status(),
                "performance": await PerformanceMonitor.get_latest()
            }
            await websocket.send_json(data)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info(f"设备 {device_id} WebSocket 断开连接")
