"""
执行引擎 - 主从配合
主引擎：Qwen-VL + 动作解析器
辅引擎1：uiautomator2（控件树）
辅引擎2：Airtest（图像模板匹配）
底层驱动：ADB
"""
import asyncio
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from app.core.database import execute_query, fetch_one
from app.devices.manager import DeviceManager
from app.ai.agent import AIAgent

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """执行引擎"""
    
    def __init__(self, device_manager: DeviceManager, ai_agent: AIAgent):
        self.device_manager = device_manager
        self.ai_agent = ai_agent
        self.running_executions = {}  # execution_id -> status
        self.ui_automator_available = False
        self.airtest_available = False
        
    async def initialize(self):
        """初始化执行引擎"""
        try:
            # 检查 uiautomator2 是否可用
            await self._check_uiautomator()
            
            # 检查 Airtest 是否可用
            await self._check_airtest()
            
            logger.info("✅ 执行引擎初始化完成")
        except Exception as e:
            logger.error(f"❌ 执行引擎初始化失败: {e}")
            raise
    
    async def _check_uiautomator(self):
        """检查 uiautomator2"""
        try:
            import uiautomator2 as u2
            self.ui_automator_available = True
            logger.info("✅ uiautomator2 可用")
        except ImportError:
            logger.warning("⚠️ uiautomator2 未安装")
            self.ui_automator_available = False
    
    async def _check_airtest(self):
        """检查 Airtest"""
        try:
            import airtest
            self.airtest_available = True
            logger.info("✅ Airtest 可用")
        except ImportError:
            logger.warning("⚠️ Airtest 未安装")
            self.airtest_available = False
    
    async def execute_case(
        self,
        case_id: int,
        device_id: str,
        execution_id: int
    ) -> Dict:
        """
        执行测试用例
        支持三种模式：Python / YAML / 自然语言
        """
        try:
            # 获取用例内容
            case_row = await fetch_one(
                "SELECT * FROM test_cases WHERE id = ?",
                (case_id,)
            )
            
            if not case_row:
                return {"status": "failed", "error": "用例不存在"}
            
            case_type = case_row["type"]
            content = case_row["content"]
            
            # 根据类型执行
            if case_type == "python":
                result = await self._execute_python(content, device_id, execution_id)
            elif case_type == "yaml":
                result = await self._execute_yaml(content, device_id, execution_id)
            elif case_type == "natural":
                result = await self._execute_natural(content, device_id, execution_id)
            else:
                result = {"status": "failed", "error": f"不支持的用例类型: {case_type}"}
            
            # 更新执行状态
            await execute_query(
                "UPDATE executions SET status = ?, end_time = ? WHERE id = ?",
                (result["status"], datetime.now().isoformat(), execution_id)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"执行用例失败: {e}")
            await execute_query(
                "UPDATE executions SET status = 'failed', error_message = ? WHERE id = ?",
                (str(e), execution_id)
            )
            return {"status": "failed", "error": str(e)}
    
    async def _execute_python(
        self,
        code: str,
        device_id: str,
        execution_id: int
    ) -> Dict:
        """执行 Python 代码"""
        try:
            # 创建执行环境
            exec_globals = {
                "device": self.device_manager,
                "device_id": device_id,
                "execution_id": execution_id,
                "ai_agent": self.ai_agent,
                "asyncio": asyncio
            }
            
            # 执行代码
            exec(code, exec_globals)
            
            return {"status": "success", "message": "Python 用例执行完成"}
            
        except Exception as e:
            logger.error(f"Python 执行失败: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def _execute_yaml(
        self,
        yaml_content: str,
        device_id: str,
        execution_id: int
    ) -> Dict:
        """执行 YAML 步骤"""
        try:
            import yaml
            steps = yaml.safe_load(yaml_content)
            
            for i, step in enumerate(steps.get("steps", [])):
                action = step.get("action")
                params = step.get("params", {})
                
                # 执行步骤
                result = await self._execute_step(action, params, device_id, execution_id)
                
                if not result.get("success"):
                    return {
                        "status": "failed",
                        "error": f"步骤 {i+1} 失败: {result.get('error')}",
                        "step": i+1
                    }
            
            return {"status": "success", "message": "YAML 用例执行完成"}
            
        except Exception as e:
            logger.error(f"YAML 执行失败: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def _execute_natural(
        self,
        instruction: str,
        device_id: str,
        execution_id: int
    ) -> Dict:
        """
        执行自然语言指令
        使用 AI Agent 进行推理和规划
        """
        try:
            # 获取页面历史
            page_history = await self._get_page_history(device_id)
            
            # AI 规划动作
            screenshot_path = await self.device_manager.take_screenshot(device_id)
            if not screenshot_path:
                return {"status": "failed", "error": "截屏失败"}
            
            action = await self.ai_agent.plan_action(
                screenshot_path,
                instruction,
                page_history
            )
            
            # 执行动作
            result = await self._execute_action(action, device_id, execution_id)
            
            if result.get("success"):
                return {"status": "success", "message": "自然语言指令执行完成"}
            else:
                return {"status": "failed", "error": result.get("error")}
            
        except Exception as e:
            logger.error(f"自然语言执行失败: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def _execute_step(
        self,
        action: str,
        params: Dict,
        device_id: str,
        execution_id: int
    ) -> Dict:
        """执行单个步骤"""
        try:
            if action == "click":
                x, y = params.get("x"), params.get("y")
                success = await self.device_manager.click(device_id, x, y)
                return {"success": success}
            
            elif action == "swipe":
                x1, y1 = params.get("x1"), params.get("y1")
                x2, y2 = params.get("x2"), params.get("y2")
                duration = params.get("duration", 300)
                success = await self.device_manager.swipe(device_id, x1, y1, x2, y2, duration)
                return {"success": success}
            
            elif action == "input":
                text = params.get("text", "")
                success = await self.device_manager.input_text(device_id, text)
                return {"success": success}
            
            elif action == "press":
                key = params.get("key", "ENTER")
                keycode = self.device_manager.devices[device_id].key_mapping.get(key)
                if keycode:
                    success = await self.device_manager.press_key(device_id, keycode)
                    return {"success": success}
                return {"success": False, "error": f"未知键值: {key}"}
            
            elif action == "screenshot":
                path = await self.device_manager.take_screenshot(device_id)
                return {"success": bool(path), "screenshot_path": path}
            
            elif action == "ai_click":
                # 使用 AI 定位并点击
                target = params.get("target", "")
                return await self._ai_click(device_id, target, execution_id)
            
            else:
                return {"success": False, "error": f"未知动作: {action}"}
            
        except Exception as e:
            logger.error(f"执行步骤失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_action(
        self,
        action: Dict,
        device_id: str,
        execution_id: int
    ) -> Dict:
        """执行 AI 规划的动作"""
        try:
            action_type = action.get("type")
            coordinates = action.get("coordinates")
            text = action.get("text")
            
            if action_type == "click" and coordinates:
                x, y = coordinates[0], coordinates[1]
                success = await self.device_manager.click(device_id, x, y)
                return {"success": success}
            
            elif action_type == "swipe":
                # 需要解析滑动方向
                return {"success": False, "error": "滑动动作需要更多参数"}
            
            elif action_type == "input" and text:
                success = await self.device_manager.input_text(device_id, text)
                return {"success": success}
            
            elif action_type == "back":
                keycode = self.device_manager.devices[device_id].key_mapping.get("BACK")
                success = await self.device_manager.press_key(device_id, keycode)
                return {"success": success}
            
            elif action_type == "home":
                keycode = self.device_manager.devices[device_id].key_mapping.get("HOME")
                success = await self.device_manager.press_key(device_id, keycode)
                return {"success": success}
            
            elif action_type == "wait":
                await asyncio.sleep(1)
                return {"success": True}
            
            else:
                return {"success": False, "error": f"未知动作类型: {action_type}"}
            
        except Exception as e:
            logger.error(f"执行动作失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _ai_click(
        self,
        device_id: str,
        target: str,
        execution_id: int
    ) -> Dict:
        """使用 AI 定位并点击"""
        try:
            # 截屏
            screenshot_path = await self.device_manager.take_screenshot(device_id)
            if not screenshot_path:
                return {"success": False, "error": "截屏失败"}
            
            # 使用 AI 分析
            analysis = await self.ai_agent.analyze_image(
                screenshot_path,
                f"找到并点击 {target}"
            )
            
            # 获取坐标
            coordinates = analysis.get("coordinates")
            if coordinates:
                x, y = coordinates[0], coordinates[1]
                success = await self.device_manager.click(device_id, x, y)
                return {"success": success}
            else:
                # 降级到辅引擎
                return await self._fallback_click(device_id, target)
                
        except Exception as e:
            logger.error(f"AI 点击失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _fallback_click(
        self,
        device_id: str,
        target: str
    ) -> Dict:
        """降级点击（辅引擎）"""
        try:
            # 尝试 uiautomator2
            if self.ui_automator_available:
                import uiautomator2 as u2
                device = u2.connect(device_id)
                
                # 通过 text 查找
                element = device(text=target)
                if element.exists:
                    element.click()
                    return {"success": True, "method": "uiautomator2"}
            
            # 尝试 Airtest
            if self.airtest_available:
                # Airtest 图像匹配
                return {"success": False, "error": "Airtest 降级待实现"}
            
            return {"success": False, "error": "所有引擎都无法定位目标"}
            
        except Exception as e:
            logger.error(f"降级点击失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_page_history(self, device_id: str) -> List[str]:
        """获取页面历史"""
        try:
            from app.core.database import fetch_all
            rows = await fetch_all("""
                SELECT page_name FROM page_states
                WHERE device_id = (SELECT id FROM devices WHERE device_id = ?)
                ORDER BY created_at DESC
                LIMIT 10
            """, (device_id,))
            
            return [row["page_name"] for row in rows]
            
        except Exception as e:
            logger.error(f"获取页面历史失败: {e}")
            return []
