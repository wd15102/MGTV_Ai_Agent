"""
数据库初始化 - SQLite
存储用例、执行记录、性能数据、知识库
"""
import aiosqlite
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# 数据库路径
DB_PATH = Path(__file__).parent.parent.parent / "database" / "test_platform.db"

# 建表 SQL
SCHEMA_SQL = """
-- 用例表
CREATE TABLE IF NOT EXISTS test_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL DEFAULT 'python',  -- python/yaml/natural
    content TEXT NOT NULL,  -- 脚本内容或YAML或自然语言描述
    version TEXT,  -- Git commit hash
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 设备表
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT UNIQUE NOT NULL,  -- ADB device serial
    name TEXT,
    type TEXT NOT NULL,  -- phone/tv/box
    status TEXT DEFAULT 'offline',  -- online/offline/busy
    resolution TEXT,  -- 宽x高
    android_version TEXT,
    last_heartbeat TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 执行记录表
CREATE TABLE IF NOT EXISTS executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    device_id INTEGER NOT NULL,
    status TEXT NOT NULL,  -- pending/running/success/failed/timeout
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    error_message TEXT,
    screenshot_path TEXT,
    video_path TEXT,
    ai_analysis TEXT,  -- AI 生成的缺陷摘要
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES test_cases(id),
    FOREIGN KEY (device_id) REFERENCES devices(id)
);

-- 性能数据表
CREATE TABLE IF NOT EXISTS performance_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id INTEGER NOT NULL,
    device_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cpu_usage REAL,  -- %
    memory_usage REAL,  -- MB
    memory_percent REAL,  -- %
    fps REAL,
    temperature REAL,  -- 摄氏度
    network_rx REAL,  -- 接收字节/s
    network_tx REAL,  -- 发送字节/s
    FOREIGN KEY (execution_id) REFERENCES executions(id),
    FOREIGN KEY (device_id) REFERENCES devices(id)
);

-- 日志表
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id INTEGER,
    device_id INTEGER,
    level TEXT NOT NULL,  -- INFO/WARNING/ERROR/FATAL
    tag TEXT,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (execution_id) REFERENCES executions(id),
    FOREIGN KEY (device_id) REFERENCES devices(id)
);

-- 知识库 - 崩溃堆栈指纹
CREATE TABLE IF NOT EXISTS crash_fingerprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stack_hash TEXT UNIQUE NOT NULL,  -- SimHash
    exception_class TEXT,
    stack_top3 TEXT,  -- 前3层调用链
    solution TEXT,  -- 推荐解决方案
    occurrence_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 知识库 - 截图相似度
CREATE TABLE IF NOT EXISTS screenshot_hashes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id INTEGER,
    phash TEXT NOT NULL,  -- 感知哈希
    histogram TEXT,  -- 直方图特征
    description TEXT,  -- 截图描述
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (execution_id) REFERENCES executions(id)
);

-- 页面状态机表
CREATE TABLE IF NOT EXISTS page_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    page_name TEXT NOT NULL,
    screenshot_path TEXT,
    ui_elements TEXT,  -- JSON格式
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id)
);

-- 页面流转规则表
CREATE TABLE IF NOT EXISTS page_transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_page TEXT NOT NULL,
    to_page TEXT NOT NULL,
    action TEXT NOT NULL,  -- click/back/home/swipe
    device_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户表（简单RBAC）
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'observer',  -- admin/engineer/observer
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_executions_case ON executions(case_id);
CREATE INDEX IF NOT EXISTS idx_executions_device ON executions(device_id);
CREATE INDEX IF NOT EXISTS idx_performance_execution ON performance_data(execution_id);
CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON performance_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_execution ON logs(execution_id);
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
CREATE INDEX IF NOT EXISTS idx_crash_hash ON crash_fingerprints(stack_hash);
CREATE INDEX IF NOT EXISTS idx_screenshot_hash ON screenshot_hashes(phash);
"""

# 数据库连接池
_db_connection: Optional[aiosqlite.Connection] = None


async def get_db() -> aiosqlite.Connection:
    """获取数据库连接"""
    global _db_connection
    if _db_connection is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _db_connection = await aiosqlite.connect(str(DB_PATH))
        _db_connection.row_factory = aiosqlite.Row
        await _db_connection.execute("PRAGMA journal_mode=WAL")
        await _db_connection.execute("PRAGMA foreign_keys=ON")
    return _db_connection


async def init_db():
    """初始化数据库"""
    try:
        conn = await get_db()
        await conn.executescript(SCHEMA_SQL)
        await conn.commit()
        logger.info(f"✅ 数据库初始化完成: {DB_PATH}")
        
        # 创建默认管理员用户
        await conn.execute("""
            INSERT OR IGNORE INTO users (username, password_hash, role)
            VALUES (?, ?, ?)
        """, ("admin", "hashed_password_here", "admin"))  # 生产环境需使用安全的密码哈希
        await conn.commit()
        
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        raise


async def close_db():
    """关闭数据库连接"""
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None
        logger.info("✅ 数据库连接已关闭")


async def execute_query(query: str, params: tuple = None):
    """执行查询（INSERT/UPDATE/DELETE）"""
    conn = await get_db()
    cursor = await conn.execute(query, params or ())
    await conn.commit()
    return cursor


async def fetch_one(query: str, params: tuple = None):
    """查询单条记录"""
    conn = await get_db()
    cursor = await conn.execute(query, params or ())
    return await cursor.fetchone()


async def fetch_all(query: str, params: tuple = None):
    """查询多条记录"""
    conn = await get_db()
    cursor = await conn.execute(query, params or ())
    return await cursor.fetchall()
