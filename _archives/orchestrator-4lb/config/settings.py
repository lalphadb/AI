"""
🎛️ Configuration Orchestrateur 4LB
"""
import os
from pathlib import Path

# === Chemins de base ===
BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "logs"
BACKUPS_DIR = BASE_DIR / "backups"
TEMPLATES_DIR = BASE_DIR / "templates"

# === Serveur ===
SERVER_HOST = os.getenv("ORCHESTRATOR_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("ORCHESTRATOR_PORT", "8888"))

# === Infrastructure cible ===
INFRA_DIR = Path(os.getenv("INFRA_DIR", "/home/lalpha/projets/infrastructure/4lb-docker-stack"))
PROJECTS_DIR = Path(os.getenv("PROJECTS_DIR", "/home/lalpha/projets"))
SCRIPTS_DIR = Path(os.getenv("SCRIPTS_DIR", "/home/lalpha/scripts"))

# === Ollama (LLM local) ===
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:32b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# === PostgreSQL ===
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_DATABASES = ["ai_postgres", "open_webui"]

# === Redis ===
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# === S3/MinIO Backup ===
S3_ENABLED = os.getenv("S3_ENABLED", "false").lower() == "true"
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "https://s3.amazonaws.com")
S3_BUCKET = os.getenv("S3_BUCKET", "4lb-backups")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")

# === GitOps ===
GITOPS_ENABLED = True
GITOPS_REMOTE = os.getenv("GITOPS_REMOTE", "origin")
GITOPS_BRANCH = os.getenv("GITOPS_BRANCH", "main")
GITOPS_AUTO_COMMIT = os.getenv("GITOPS_AUTO_COMMIT", "true").lower() == "true"

# === Self-Improvement ===
SELF_IMPROVE_ENABLED = True
SELF_IMPROVE_SCHEDULE = "0 6 * * *"  # 6h00 quotidien
ANOMALY_THRESHOLD = 0.8  # Score de confiance pour alerter

# === Sécurité ===
PROTECTED_PATHS = [
    "/etc",
    "/root",
    "/var/lib/docker",
    str(INFRA_DIR / "docker-compose.yml"),
    str(INFRA_DIR / "traefik"),
]

ALLOWED_COMMANDS = [
    "docker", "docker-compose", "docker compose",
    "systemctl", "journalctl",
    "ls", "cat", "grep", "find", "df", "du",
    "curl", "wget",
    "git", "npm", "node", "python3",
    "ollama", "nvidia-smi",
]

# === Logging ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# === Créer les dossiers si nécessaire ===
LOGS_DIR.mkdir(exist_ok=True)
BACKUPS_DIR.mkdir(exist_ok=True)
