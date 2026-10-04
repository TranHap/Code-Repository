"""Chemins et paramètres partagés."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = Path(__file__).resolve().parent
DATA = PKG / "data"
DB_PATH = Path(os.environ.get("NOVA_DB", DATA / "memory.db"))   # NOVA_DB : autre base (tests, démo)
VISION_CACHE = DATA / "vision_cache.json"
CORPUS_DEFAULT = ROOT / "NOVA_ETUDIANTS" / "Projet360_NOVA_ETUDIANTS"


def load_env() -> dict:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return {}
    return dict(l.split("=", 1) for l in env_file.read_text(encoding="utf-8").splitlines() if "=" in l)


ENV = load_env()
LLM_BASE_URL = ENV.get("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4/")
LLM_API_KEY = ENV.get("ZAI_API_KEY", "")
TEXT_MODEL = ENV.get("TEXT_MODEL", "glm-4.7-flash")
VISION_MODEL = ENV.get("VISION_MODEL", "glm-4.6v-flash")

# print(LLM_BASE_URL)