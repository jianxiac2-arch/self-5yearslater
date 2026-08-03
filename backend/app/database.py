"""SQLite 数据库：分层记忆库的结构化存储。

schema 对应 spec.md 第 4 节。直接用 sqlite3 标准库，轻量零运维。
"""
import sqlite3
from app.config import settings

# 完整 schema，对应 spec 第 4 节数据模型
SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    key TEXT PRIMARY KEY,
    value TEXT,
    confidence REAL,
    source TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    category TEXT,
    content TEXT,
    importance REAL DEFAULT 0.5,
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    vector_id TEXT
);

CREATE TABLE IF NOT EXISTS preferences (
    id TEXT PRIMARY KEY,
    type TEXT,
    content TEXT,
    importance REAL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS episodes (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    summary TEXT,
    importance REAL DEFAULT 0.5,
    topics TEXT,
    entities TEXT,
    vector_id TEXT
);

CREATE TABLE IF NOT EXISTS reflections (
    id TEXT PRIMARY KEY,
    type TEXT,
    content TEXT,
    evidence TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    vector_id TEXT
);

CREATE TABLE IF NOT EXISTS frameworks (
    id TEXT PRIMARY KEY,
    type TEXT,
    name TEXT,
    content TEXT,
    trigger_conditions TEXT,
    vector_id TEXT
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    role TEXT,
    content TEXT,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category);
CREATE INDEX IF NOT EXISTS idx_episodes_conv ON episodes(conversation_id);
CREATE INDEX IF NOT EXISTS idx_episodes_occurred ON episodes(occurred_at);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_frameworks_type ON frameworks(type);
"""


def get_db() -> sqlite3.Connection:
    """获取一个 SQLite 连接（row 工厂为 Row，方便按列名取值）。"""
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """初始化数据库：建表。幂等，可重复执行。"""
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
