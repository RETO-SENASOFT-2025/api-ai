import os

DB_PATH = os.getenv("DB_PATH", "data/db/reports.sqlite")
LLM_URL = os.getenv("LLM_URL", "http://localhost:8081")
MAX_CTX_DOCS = int(os.getenv("MAX_CTX_DOCS", "8"))
N_PREDICT = int(os.getenv("N_PREDICT", "128"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
TOP_K = int(os.getenv("TOP_K", "40"))
TOP_P = float(os.getenv("TOP_P", "0.9"))
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "180"))