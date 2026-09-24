"""
配置常量和环境变量
"""

import os
from pathlib import Path


SERVICE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("TIKU_DATA_DIR", SERVICE_DIR / "data")).resolve()
LEGACY_SERVICE_DIR = SERVICE_DIR


def _runtime_path(filename: str) -> str:
    """返回运行时文件路径，并兼容整理前的 tiku 根目录文件。"""
    env_names = {
        "questions.db": "DATABASE_FILE",
        "tiku.json": "JSON_FILE",
        "config.json": "CONFIG_FILE",
    }
    configured = os.environ.get(env_names[filename])
    if configured:
        return str(Path(configured).expanduser().resolve())

    current = DATA_DIR / filename
    legacy = LEGACY_SERVICE_DIR / filename
    if not current.exists() and legacy.exists():
        return str(legacy)
    return str(current)

# ============ 数据库配置 ============
DATABASE_FILE = _runtime_path("questions.db")
JSON_FILE = _runtime_path("tiku.json")
CONFIG_FILE = os.environ.get("CONFIG_FILE", _runtime_path("config.json"))

# ============ 服务器配置 ============
API_KEY = os.environ.get("API_KEY", "your_api_key")
DEFAULT_PORT = 8002

# ============ 请求限制 ============
MAX_QUESTION_LENGTH = 10000
MAX_OPTIONS_COUNT = 20
MAX_SEARCH_LENGTH = 500
MAX_LIMIT = 1000
MAX_OFFSET = 100000

# ============ 限流配置 ============
RATE_LIMIT_REQUESTS = 200
RATE_LIMIT_WINDOW = 60
REQUEST_TIMEOUT = 30
MAX_CONCURRENT_REQUESTS = 150
