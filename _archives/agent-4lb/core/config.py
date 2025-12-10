"""
🧠 Configuration Agent 4LB - Chef d'Orchestre Autonome
"""
import os
from pathlib import Path

# === Chemins ===
BASE_DIR = Path(__file__).parent.parent
MEMORY_DIR = BASE_DIR / "memory"
LOGS_DIR = BASE_DIR / "logs"

# Créer les dossiers
MEMORY_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# === LLM Configuration ===
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:32b-instruct-q4_K_M")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.1"))

# Claude API (Optionnel)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# Quel LLM utiliser
DEFAULT_LLM = os.getenv("DEFAULT_LLM", "ollama")

# === Agent Configuration ===
AGENT_NAME = "Agent 4LB"
AGENT_MAX_ITERATIONS = int(os.getenv("AGENT_MAX_ITERATIONS", "15"))
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "300"))

# === Mémoire ===
MEMORY_TYPE = os.getenv("MEMORY_TYPE", "sqlite")
MEMORY_DB_PATH = MEMORY_DIR / "agent_memory.db"
CONVERSATION_HISTORY_LIMIT = 50

# === Infrastructure ===
INFRA_DIR = Path(os.getenv("INFRA_DIR", "/home/lalpha/projets/infrastructure/4lb-docker-stack"))
PROJECTS_DIR = Path(os.getenv("PROJECTS_DIR", "/home/lalpha/projets"))
SCRIPTS_DIR = Path(os.getenv("SCRIPTS_DIR", "/home/lalpha/scripts"))

# === Sécurité ===
PROTECTED_PATHS = ["/etc/passwd", "/etc/shadow", "/root"]
DANGEROUS_COMMANDS = ["rm -rf /", "mkfs", "dd if=", "> /dev/sda"]

# === API Server ===
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8889"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
