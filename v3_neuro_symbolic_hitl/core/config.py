import os
from pathlib import Path

# ==========================================
# 1. 大模型 API 配置
# ==========================================
DEEPSEEK_API_KEY = os.getenv("MOONSHOT_API_KEY", "sk-这里替换成你的真实APIKey")
BASE_URL = "https://api.moonshot.cn/v1"
MODEL_NAME = "kimi-k2.5"

# ==========================================
# 2. 本地数据与日志路径配置
# ==========================================
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(exist_ok=True)

DB_PATH = str(DATA_DIR / "ecommerce.db")
LOG_PATH = str(DATA_DIR / "audit_logs.jsonl")
# --- HITL (Human-in-the-loop) 配置 ---
ENABLE_HUMAN_IN_THE_LOOP = True
EXPERIENCE_DB_PATH = "data/experience_pool.jsonl"