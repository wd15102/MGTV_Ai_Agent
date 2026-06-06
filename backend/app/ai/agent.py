"""
AI Agent - 决策大脑
实现分级推理策略：简单任务用小模型，复杂任务用大模型
支持 Qwen2.5-7B（通过 Ollama 远程调用）
"""
import asyncio
import logging
import base64
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import aiohttp

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIAgent:
    """AI 决策引擎"""
    
    def __init__(self):
        self.qwen_enabled = settings.QWEN_ENABLE
        self.qwen_base_url = settings.QWEN_OLLAMA_BASE_URL  # 从配置读取
        self.qwen_model = settings.QWEN_OLLAMA_MODEL  # 使用 qwen2.5:7b
        self.qwen_timeout = settings.QWEN_INFERENCE_TIMEOUT
        self.yolo_enabled = settings.YOLO_ENABLE
        self.ocr_enabled = settings.PADDLE_OCR_ENABLE
        self.fallback_enabled = settings.FALLBACK_ENABLE
        
        # 状态
        self.status = "initializing"  # initializing/ready/error
        self.current_task = None
        self.thought_history = []  # Thought-Action-Observation 历史
        
    async def initialize(self):
        """初始化 AI 模型"""
        try:
            logger.info("正在初始化 AI Agent...")
            
            # 检查 Qwen 是否可用
            if self.qwen_enabled:
                await self._check_qwen_availability()
            
            # 初始化 YOLO
            if self.yolo_enabled:
                await self._initialize_yolo()
            
            # 初始化 OCR
            if self.ocr_enabled:
                await self._initialize_ocr()
            
            self.status = "ready"
            logger.info("AI Agent 初始化完成")
            
        except Exception as e:
            self.status = "error"
            logger.error(f"AI Agent 初始化失败: {e}")
            raise
    
    async def _check_qwen_availability(self):
        """检查 Qwen 服务是否可用"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.qwen_base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m["name"] for m in data.get("models", [])]
                        if self.qwen_model not in models:
                            logger.warning(f"模型 {self.qwen_model} 未找到，可用模型: {models}")
                        else:
                            logger.info(f"Qwen 模型可用: {self.qwen_model}")
        except Exception as e:
            logger.warning(f"Qwen 服务不可用: {e}")
            self.qwen_enabled = False
    
    async def _initialize_yolo(self):
        """初始化 YOLOv8"""
        try:
            from ultralytics import YOLO
            model_path = Path(settings.YOLO_MODEL_PATH)
            if model_path.exists():
                self.yolo_model = YOLO(str(model_path))
                logger.info(f"YOLOv8 模型加载成功: {model_path}")
            else:
                logger.warning(f"YOLOv8 模型文件不存在: {model_path}")
                self.yolo_enabled = False
        except Exception as e:
            logger.warning(f"YOLOv8 初始化失败: {e}")
            self.yolo_enabled = False
    
    async def _initialize_ocr(self):
        """初始化 RapidOCR"""
        try:
            from rapidocr import RapidOCR
            self.ocr = RapidOCR(use_angle_cls=True, lang='ch', show_log=False)
            logger.info("RapidOCR 初始化成功")
        except Exception as e:
            logger.warning(f"RapidOCR 初始化失败: {e}")
            self.ocr_enabled = False
    
    async def analyze_image(
        self, 
        image_path: str, 
        task: str,
        confidence_threshold: float = 0.85
    ) -> Dict:
        """
        分析图像并执行任务
        分级推理策略：
        1. 简单任务 → YOLOv8 / RapidOCR（< 50ms）
        2. 复杂任务 → Qwen2.5-7B（> 3s）
        """
        try:
            # 读取图像
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # 判断任务类型
            task_type = self._classify_task(task)
            
            result = {}
            
            # 简单任务：使用小模型
            if task_type in ["detect_ui", "extract_text", "find_icon"]:
                if task_type == "detect_ui" and self.yolo_enabled:
                    result = await self._yolo_detect(image_path, confidence_threshold)
                elif task_type == "extract_text" and self.ocr_enabled:
                    result = await self._ocr_extract(image_path)
                elif task_type == "find_icon" and self.yolo_enabled:
                    result = await self._yolo_detect(image_path, confidence_threshold)
                
                # 检查置信度
                if result.get("confidence", 0) >= confidence_threshold:
                    return result
                elif result.get("confidence", 0) >= 0.5:
                    # 置信度中等：异步调用大模型复核，同时使用小模型结果
                    logger.info("置信度中等，异步调用大模型复核...")
                    asyncio.create_task(self._qwen_analyze(image_data, task))
                    return result
            
            # 复杂任务或置信度低：使用大模型
            if self.qwen_enabled:
                result = await self._qwen_analyze(image_data, task)
            else:
                # 降级到辅引擎
                if self.fallback_enabled:
                    result = await self._fallback(task_type, image_path)
            
            return result
            
        except Exception as e:
            logger.error(f"图像分析失败: {e}")
            return {"error": str(e)}
    
    def _classify_task(self, task: str) -> str:
        """分类任务类型"""
        task_lower = task.lower()
        if any(kw in task_lower for kw in ["检测", "detect", "找图标", "find icon", "ui元素"]):
            return "detect_ui"
        elif any(kw in task_lower for kw in ["文字", "text", "识别", "ocr", "提取"]):
            return "extract_text"
        elif any(kw in task_lower for kw in ["点击", "click", "滑动", "swipe", "输入", "input"]):
            return "action_planning"
        else:
            return "complex_analysis"
    
    async def _yolo_detect(self, image_path: str, conf_threshold: float) -> Dict:
        """YOLOv8 UI 元素检测"""
        try:
            results = self.yolo_model(image_path, conf=conf_threshold)[0]
            
            detections = []
            for box in results.boxes:
                detections.append({
                    "class": results.names[int(box.cls)],
                    "confidence": float(box.conf),
                    "bbox": [float(x) for x in box.xyxy[0].tolist()]  # [x1, y1, x2, y2]
                })
            
            return {
                "source": "yolo",
                "detections": detections,
                "confidence": max([d["confidence"] for d in detections], default=0)
            }
        except Exception as e:
            logger.error(f"YOLO 检测失败: {e}")
            return {"error": str(e)}
    
    async def _ocr_extract(self, image_path: str) -> Dict:
        """RapidOCR 文字识别"""
        try:
            result = self.ocr(image_path)
            
            texts = []
            if result and result.txts:
                for i, text in enumerate(result.txts):
                    texts.append({
                        "text": text,
                        "confidence": float(result.scores[i]),
                        "bbox": result.boxes[i].tolist()  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    })
            
            return {
                "source": "ocr",
                "texts": texts,
                "confidence": max([t["confidence"] for t in texts], default=0)
            }
        except Exception as e:
            logger.error(f"OCR 识别失败: {e}")
            return {"error": str(e)}
    
    async def _qwen_analyze(self, image_data: str, task: str) -> Dict:
        """调用 Qwen 进行复杂分析"""
        try:
            prompt = f"""
            你是一个移动应用测试专家。请分析这张截图，完成以下任务：
            {task}
            
            请以 JSON 格式返回结果，包含：
            - action: 需要执行的动作（click/swipe/input/wait/back/home）
            - coordinates: 坐标 [x, y]（如果需要点击）
            - confidence: 置信度 (0-1)
            - reasoning: 推理过程
            """
            
            payload = {
                "model": self.qwen_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                        ]
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 512
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.qwen_base_url}/v1/chat/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.qwen_timeout)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        content = data["choices"][0]["message"]["content"]
                        
                        # 尝试解析 JSON
                        try:
                            result = json.loads(content)
                        except:
                            result = {"reasoning": content}
                        
                        result["source"] = "qwen"
                        return result
                    else:
                        logger.error(f"Qwen 调用失败: {resp.status}")
                        return {"error": f"Qwen 调用失败: {resp.status}"}
                        
        except asyncio.TimeoutError:
            logger.warning(f"Qwen 推理超时 ({self.qwen_timeout}秒)")
            return {"error": "timeout", "fallback": True}
        except Exception as e:
            logger.error(f"Qwen 分析失败: {e}")
            return {"error": str(e)}
    
    async def _fallback(self, task_type: str, image_path: str) -> Dict:
        """降级策略"""
        logger.info(f"执行降级策略: {task_type}")
        
        if task_type == "extract_text":
            # OCR 失败 → 尝试 UI 控件树
            return {"source": "fallback", "method": "ui_tree", "message": "请使用 uiautomator2 获取控件树"}
        
        elif task_type == "detect_ui":
            # YOLO 失败 → 尝试图像模板匹配
            return {"source": "fallback", "method": "template_matching", "message": "请使用 Airtest 进行图像匹配"}
        
        else:
            return {"source": "fallback", "method": "manual", "message": "需要人工介入"}
    
    def get_status(self) -> Dict:
        """获取 AI Agent 状态"""
        return {
            "status": self.status,
            "qwen_enabled": self.qwen_enabled,
            "yolo_enabled": self.yolo_enabled,
            "ocr_enabled": self.ocr_enabled,
            "current_task": self.current_task,
            "thought_history_len": len(self.thought_history)
        }
    
    async def plan_action(
        self, 
        screenshot_path: str, 
        goal: str,
        page_history: List[str]
    ) -> Dict:
        """
        路径规划 - 根据当前截图和历史页面，自动决策下一步动作
        实现 Thought-Action-Observation 循环
        """
        try:
            # 记录 Thought
            thought = f"当前目标: {goal}, 历史页面: {page_history}"
            self.thought_history.append({
                "thought": thought,
                "timestamp": datetime.now().isoformat()
            })
            
            # 分析当前截图
            analysis = await self.analyze_image(screenshot_path, goal)
            
            # 生成动作
            action = {
                "type": analysis.get("action", "wait"),
                "coordinates": analysis.get("coordinates"),
                "text": analysis.get("text"),
                "reasoning": analysis.get("reasoning", ""),
                "confidence": analysis.get("confidence", 0)
            }
            
            # 记录 Action
            self.thought_history.append({
                "action": action,
                "timestamp": datetime.now().isoformat()
            })
            
            return action
            
        except Exception as e:
            logger.error(f"路径规划失败: {e}")
            return {"type": "error", "message": str(e)}
