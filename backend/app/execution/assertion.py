"""
断言层 - L1/L2/L3 三级断言
L1: 规则断言（控件属性）
L2: OCR 断言（屏幕文字）
L3: AI 视觉断言（UI 异常检测、页面完整度）
"""
import asyncio
import logging
from typing import Dict, List, Optional
from pathlib import Path
import re

logger = logging.getLogger(__name__)


class AssertionLayer:
    """断言层"""
    
    def __init__(self, device_manager, ai_agent):
        self.device_manager = device_manager
        self.ai_agent = ai_agent
        self.yolo_enabled = True
        self.ocr_enabled = True
        
    async def assert(
        self,
        level: int,
        device_id: str,
        assertion_config: Dict
    ) -> Dict:
        """
        执行断言
        :param level: 断言级别 (1/2/3)
        :param device_id: 设备 ID
        :param assertion_config: 断言配置
        :return: 断言结果
        """
        try:
            if level == 1:
                return await self._assert_l1(device_id, assertion_config)
            elif level == 2:
                return await self._assert_l2(device_id, assertion_config)
            elif level == 3:
                return await self._assert_l3(device_id, assertion_config)
            else:
                return {"success": False, "error": f"不支持的断言级别: {level}"}
        except Exception as e:
            logger.error(f"断言失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _assert_l1(self, device_id: str, config: Dict) -> Dict:
        """
        L1 规则断言
        检查控件属性（文本/可见性/存在性）
        """
        try:
            if not self.device_manager.ui_automator_available:
                return {"success": False, "error": "uiautomator2 不可用"}
            
            import uiautomator2 as u2
            device = u2.connect(device_id)
            
            checks = config.get("checks", [])
            results = []
            
            for check in checks:
                check_type = check.get("type")
                target = check.get("target")
                
                if check_type == "exists":
                    # 检查元素是否存在
                    element = device(**target)
                    result = element.exists
                    results.append({
                        "check": check_type,
                        "target": target,
                        "expected": True,
                        "actual": result,
                        "success": result == True
                    })
                
                elif check_type == "text_equals":
                    # 检查文本相等
                    element = device(**target)
                    if element.exists:
                        actual_text = element.get_text()
                        expected_text = check.get("expected")
                        result = actual_text == expected_text
                        results.append({
                            "check": check_type,
                            "target": target,
                            "expected": expected_text,
                            "actual": actual_text,
                            "success": result
                        })
                    else:
                        results.append({
                            "check": check_type,
                            "target": target,
                            "success": False,
                            "error": "元素不存在"
                        })
                
                elif check_type == "visible":
                    # 检查可见性
                    element = device(**target)
                    if element.exists:
                        result = element.info.get("visible", False)
                        results.append({
                            "check": check_type,
                            "target": target,
                            "expected": True,
                            "actual": result,
                            "success": result == True
                        })
                    else:
                        results.append({
                            "check": check_type,
                            "target": target,
                            "success": False,
                            "error": "元素不存在"
                        })
            
            # 汇总结果
            all_passed = all([r.get("success") for r in results])
            return {
                "success": all_passed,
                "level": 1,
                "results": results,
                "message": "L1 断言通过" if all_passed else "L1 断言失败"
            }
            
        except Exception as e:
            logger.error(f"L1 断言失败: {e}")
            return {"success": False, "level": 1, "error": str(e)}
    
    async def _assert_l2(self, device_id: str, config: Dict) -> Dict:
        """
        L2 OCR 断言
        识别屏幕文字并检查
        """
        try:
            if not self.ocr_enabled:
                return {"success": False, "error": "OCR 不可用"}
            
            # 截屏
            screenshot_path = await self.device_manager.take_screenshot(device_id)
            if not screenshot_path:
                return {"success": False, "error": "截屏失败"}
            
            # OCR 识别
            from paddleocr import PaddleOCR
            ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
            result = ocr.ocr(screenshot_path, cls=True)
            
            # 提取文字
            texts = []
            if result and result[0]:
                for line in result[0]:
                    texts.append(line[1][0])
            
            # 检查配置
            expected_texts = config.get("expected_texts", [])
            forbidden_texts = config.get("forbidden_texts", [])
            
            results = []
            
            # 检查期望文字
            for expected in expected_texts:
                found = any(expected in text for text in texts)
                results.append({
                    "check": "text_exists",
                    "expected": expected,
                    "found": found,
                    "success": found
                })
            
            # 检查禁止文字
            for forbidden in forbidden_texts:
                found = any(forbidden in text for text in texts)
                results.append({
                    "check": "text_not_exists",
                    "forbidden": forbidden,
                    "found": found,
                    "success": not found
                })
            
            all_passed = all([r.get("success") for r in results])
            return {
                "success": all_passed,
                "level": 2,
                "results": results,
                "detected_texts": texts,
                "message": "L2 断言通过" if all_passed else "L2 断言失败"
            }
            
        except Exception as e:
            logger.error(f"L2 断言失败: {e}")
            return {"success": False, "level": 2, "error": str(e)}
    
    async def _assert_l3(self, device_id: str, config: Dict) -> Dict:
        """
        L3 AI 视觉断言
        检测 UI 异常（元素重叠/截断/错位）
        页面完整度评分
        """
        try:
            if not self.ai_agent or not self.ai_agent.enabled:
                return {"success": False, "error": "AI Agent 不可用"}
            
            # 截屏
            screenshot_path = await self.device_manager.take_screenshot(device_id)
            if not screenshot_path:
                return {"success": False, "error": "截屏失败"}
            
            # 使用 YOLO 检测 UI 元素
            if self.yolo_enabled:
                yolo_result = await self.ai_agent.analyze_image(
                    screenshot_path,
                    "detect_ui"
                )
                
                detections = yolo_result.get("detections", [])
                
                # 检查 UI 异常
                ui_issues = self._check_ui_issues(detections)
                
                # 页面完整度评分
                completeness_score = self._calculate_completeness(detections, config)
                
                results = []
                
                # 检查 UI 异常
                if ui_issues:
                    results.append({
                        "check": "ui_abnormality",
                        "issues": ui_issues,
                        "success": False
                    })
                
                # 检查页面完整度
                min_score = config.get("min_completeness", 80)
                if completeness_score < min_score:
                    results.append({
                        "check": "completeness",
                        "score": completeness_score,
                        "min_required": min_score,
                        "success": False
                    })
                
                all_passed = len([r for r in results if not r.get("success")]) == 0
                
                return {
                    "success": all_passed,
                    "level": 3,
                    "results": results,
                    "completeness_score": completeness_score,
                    "ui_issues": ui_issues,
                    "message": "L3 断言通过" if all_passed else "L3 断言失败"
                }
            else:
                return {"success": False, "error": "YOLO 不可用"}
                
        except Exception as e:
            logger.error(f"L3 断言失败: {e}")
            return {"success": False, "level": 3, "error": str(e)}
    
    def _check_ui_issues(self, detections: List[Dict]) -> List[str]:
        """检查 UI 异常（重叠/截断/错位）"""
        issues = []
        
        # 检查重叠
        for i, det1 in enumerate(detections):
            for j, det2 in enumerate(detections):
                if i >= j:
                    continue
                
                box1 = det1.get("bbox", [0, 0, 0, 0])
                box2 = det2.get("bbox", [0, 0, 0, 0])
                
                # 计算 IOU
                iou = self._calculate_iou(box1, box2)
                if iou > 0.5:  # 重叠阈值
                    issues.append(f"元素重叠: {det1.get('class')} 和 {det2.get('class')}")
        
        return issues
    
    def _calculate_iou(self, box1: List[float], box2: List[float]) -> float:
        """计算 IOU（交并比）"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        if x2 < x1 or y2 < y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def _calculate_completeness(self, detections: List[Dict], config: Dict) -> float:
        """计算页面完整度评分（0-100）"""
        required_elements = config.get("required_elements", [])
        
        if not required_elements:
            return 100.0
        
        found_count = 0
        for req in required_elements:
            for det in detections:
                if det.get("class") == req:
                    found_count += 1
                    break
        
        score = (found_count / len(required_elements)) * 100
        return round(score, 2)
