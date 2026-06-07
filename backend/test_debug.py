"""
测试 Debug 输出 - 验证 PyCharm 控制台是否显示日志
"""
import logging
import time

# 配置日志（显示 DEBUG 级别）
logging.basicConfig(
    level=logging.DEBUG,  # ← 关键！设置为 DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # 输出到控制台
    ]
)

logger = logging.getLogger(__name__)

def test_debug_output():
    """测试各种级别的日志"""
    print("=" * 60)
    print("测试 Debug 输出")
    print("=" * 60)
    
    # 1. print() 语句（会立即显示，因为设置了 PYTHONUNBUFFERED=1）
    print("✅ print() 语句：这是普通打印")
    time.sleep(0.5)
    
    # 2. logging.debug() - Debug 级别
    logger.debug("🐛 这是 DEBUG 日志（详细调试信息）")
    time.sleep(0.5)
    
    # 3. logging.info() - Info 级别
    logger.info("ℹ️ 这是 INFO 日志（正常流程）")
    time.sleep(0.5)
    
    # 4. logging.warning() - Warning 级别
    logger.warning("⚠️ 这是 WARNING 日志（警告信息）")
    time.sleep(0.5)
    
    # 5. logging.error() - Error 级别
    logger.error("❌ 这是 ERROR 日志（错误信息）")
    time.sleep(0.5)
    
    # 6. 模拟异常
    try:
        result = 1 / 0
    except Exception as e:
        logger.exception("💥 捕获到异常：")  # ← 会打印完整堆栈！
    
    print("=" * 60)
    print("测试完成！如果你在 PyCharm 控制台看到以上输出，说明配置成功！")
    print("=" * 60)

if __name__ == "__main__":
    test_debug_output()
