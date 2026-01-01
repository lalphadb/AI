#!/usr/bin/env python3
"""
Orchestrateur IA 4LB.ca - Backend FastAPI v3.0
Agent autonome avec boucle ReAct, sélection auto de modèle, upload fichiers
Sécurité: JWT, Rate Limiting, Validation commandes/chemins
"""

import asyncio
import base64
import logging
import os
import sqlite3
import subprocess
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import chromadb
import httpx
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ===== LOGGING CONFIGURATION =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler("server.log"), logging.StreamHandler()],
)
logger = logging.getLogger("api")

# ===== MODULES DE SÉCURITÉ v3.0 =====
try:
    from security import (
        CommandNotAllowedError,
        PathNotAllowedError,
        audit_log,
        get_security_config,
        is_path_allowed,
        validate_command,
        validate_path,
    )

    SECURITY_ENABLED = True
except ImportError:
    SECURITY_ENABLED = False
    logger.warning("⚠️ Module security non disponible - Validation désactivée")

try:
    from auth import (
        AUTH_ENABLED,
        APIKey,
        Token,
        User,
        UserCreate,
        UserUpdate,
        authenticate_user,
        check_login_rate_limit,
        create_access_token,
        create_api_key,
        create_refresh_token,
        create_user,
        get_current_active_user,
        get_current_admin_user,
        get_current_user,
        get_optional_user,
        get_user,
        get_user_by_id,
        get_user_id,
        init_auth_db,
        record_login_attempt,
        require_scope,
        revoke_refresh_token,
        update_user,
        verify_refresh_token,
        verify_token,
    )
except ImportError:
    AUTH_ENABLED = False
    logger.warning("⚠️ Module auth non disponible - Authentification désactivée")

try:
    from rate_limiter import RateLimitMiddleware, cleanup_task, get_rate_limit_stats, rate_limiter

    RATE_LIMIT_ENABLED = True
except ImportError:
    RATE_LIMIT_ENABLED = False
    logger.warning("⚠️ Module rate_limiter non disponible - Rate limiting désactivé")

try:
    from config import MODELS as CONFIG_MODELS
    from config import get_cors_config, get_settings

    CONFIG_ENABLED = True
except ImportError:
    CONFIG_ENABLED = False
    logger.warning("⚠️ Module config non disponible - Configuration par défaut")

try:
    from prompts import build_system_prompt, get_initial_memory_prompt, get_urgency_message

    PROMPTS_ENABLED = True
except ImportError:
    PROMPTS_ENABLED = False
    logger.warning("⚠️ Module prompts non disponible - Prompts par défaut")

# ===== NOUVEAUX MODULES v4.0 =====
try:
    from tools import TOOLS_DEFINITIONS, get_tools_description
    from tools import execute_tool as tools_execute_tool
    from utils.async_subprocess import run_command_async, run_multiple_commands

    TOOLS_MODULE_ENABLED = True
    logger.info("✅ Modules tools v4.0 chargés")
except ImportError as e:
    TOOLS_MODULE_ENABLED = False
    logger.error(f"⚠️ Modules tools v4.0 non disponibles: {e}")

try:
    from dynamic_context import get_dynamic_context

    DYNAMIC_CONTEXT_ENABLED = True
except ImportError:
    DYNAMIC_CONTEXT_ENABLED = False
    logger.warning("⚠️ Module dynamic_context non disponible")


# Helper pour protection optionnelle des endpoints
def optional_auth():
    """Retourne une dépendance d'auth si AUTH_ENABLED, sinon None"""
    if AUTH_ENABLED:
        return Depends(get_optional_user)
    return None


# Helper pour protection obligatoire des endpoints
def require_auth():
    """Retourne une dépendance d'auth obligatoire si AUTH_ENABLED"""
    if AUTH_ENABLED:
        return Depends(get_current_active_user)
    return None


# Désactiver la télémétrie ChromaDB pour éviter l'erreur capture()
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# Patch posthog pour éviter l'erreur "capture() takes 1 positional argument but 3 were given"
try:
    import posthog

    posthog.disabled = True
    # Remplacer capture par une fonction vide
    posthog.capture = lambda *args, **kwargs: None
except ImportError:
    pass

# Module d'auto-apprentissage
try:
    from auto_learn import (
        auto_learn_from_message,
        get_memory_stats,
        get_relevant_context,
        get_user_preferences,
        save_conversation_summary,
    )

    AUTO_LEARN_ENABLED = True
except ImportError:
    AUTO_LEARN_ENABLED = False
    logger.warning("⚠️ Module auto_learn non disponible")

# ===== SELF HEALING v5.0 =====
try:
    from services.self_healing import service as self_healing_service

    SELF_HEALING_ENABLED = True
except ImportError as e:
    SELF_HEALING_ENABLED = False
    logger.warning(f"⚠️ Module self_healing non disponible: {e}")

# ===== CONFIGURATION =====

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://10.10.10.46:11434")
DB_PATH = "data/orchestrator.db"
UPLOAD_DIR = "data/uploads"
# ChromaDB pour mémoire sémantique
CHROMADB_HOST = os.getenv("CHROMADB_HOST", "localhost")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8000"))


def get_chroma_client():
    """Obtenir le client ChromaDB"""
    try:
        client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        return client
    except Exception as e:
        print(f"Erreur ChromaDB: {e}")
        return None


def get_memory_collection():
    """Obtenir ou créer la collection de mémoire"""
    client = get_chroma_client()
    if client:
        return client.get_or_create_collection(
            name="ai_orchestrator_memory",
            metadata={"description": "Mémoire sémantique de l'AI Orchestrator"},
        )
    return None


MAX_ITERATIONS = 20

# Modèles disponibles avec leurs spécialités
MODELS = {
    "auto": {
        "name": "AUTO (Sélection automatique)",
        "description": "L'agent choisit le meilleur modèle selon la tâche",
        "model": None,
        "category": "auto",
    },
    # === 💻 MODÈLES CODE (Locaux) ===
    "qwen-coder": {
        "name": "Qwen 2.5 Coder 32B",
        "description": "Code, scripts, debug, analyse technique",
        "model": "qwen2.5-coder:32b-instruct-q4_K_M",
        "category": "code",
        "local": True,
        "keywords": ["code", "script", "python", "bash", "debug", "fonction", "variable", "api", "docker", "git", "npm", "programm"],
    },
    "deepseek-coder": {
        "name": "DeepSeek Coder 33B",
        "description": "Code alternatif, algorithmes complexes",
        "model": "deepseek-coder:33b",
        "category": "code",
        "local": True,
        "keywords": ["algorithme", "optimis", "complex", "performance", "refactor"],
    },
    # === 👁️ MODÈLES VISION (Locaux) ===
    "llama-vision": {
        "name": "Llama 3.2 Vision 11B",
        "description": "Analyse d'images, OCR, vision",
        "model": "llama3.2-vision:11b-instruct-q8_0",
        "category": "vision",
        "local": True,
        "keywords": ["image", "photo", "screenshot", "capture", "voir", "regarde", "analyse visuel", "ocr"],
    },
    "qwen-vision": {
        "name": "Qwen3 VL 32B",
        "description": "Vision multimodale avancée",
        "model": "qwen3-vl:32b",
        "category": "vision",
        "local": True,
        "keywords": ["image", "multimodal", "vision", "graphique", "diagramme", "schéma"],
    },
    # === 🛡️ MODÈLES SÉCURITÉ (Locaux) ===
    "gpt-safeguard": {
        "name": "GPT Safeguard 13B",
        "description": "GPT Open Source local (sécurité, modération)",
        "model": "gpt-oss-safeguard:latest",
        "category": "security",
        "local": True,
        "keywords": ["gpt", "safeguard", "sécurité", "modération"],
    },
    # === ☁️ MODÈLES CLOUD ===
    "qwen3-coder-cloud": {
        "name": "Qwen3 Coder 480B",
        "description": "Qwen3 Coder géant - Ultra performant",
        "model": "qwen3-coder:480b-cloud",
        "category": "cloud",
        "local": False,
        "keywords": ["qwen", "cloud", "coder", "gros"],
    },
    "kimi-k2": {
        "name": "Kimi K2 1T",
        "description": "Modèle cloud Kimi (Moonshot AI) - Ultra rapide",
        "model": "kimi-k2:1t-cloud",
        "category": "cloud",
        "local": False,
        "keywords": ["kimi", "moonshot", "cloud", "chinois"],
    },
    "gemini-pro": {
        "name": "Gemini 3 Pro",
        "description": "Google Gemini Pro via cloud",
        "model": "gemini-3-pro-preview:latest",
        "category": "cloud",
        "local": False,
        "keywords": ["gemini", "google", "cloud"],
    },
    # === 📊 MODÈLES EMBEDDINGS (pour RAG) ===
    "nomic-embed": {
        "name": "Nomic Embed Text",
        "description": "Embeddings pour RAG (274 MB)",
        "model": "nomic-embed-text:latest",
        "category": "embedding",
        "local": True,
        "chat": False,
    },
    "mxbai-embed": {
        "name": "MXBai Embed Large",
        "description": "Embeddings haute qualité (669 MB)",
        "model": "mxbai-embed-large:latest",
        "category": "embedding",
        "local": True,
        "chat": False,
    },
    "bge-m3": {
        "name": "BGE-M3 Multilingue",
        "description": "Embeddings multilingues FR/EN (1.2 GB) - RAG Apogée",
        "model": "bge-m3:latest",
        "category": "embedding",
        "local": True,
        "chat": False,
    },
    "bge-reranker": {
        "name": "BGE Reranker v2 M3",
        "description": "Reranking multilingue pour filtrer les résultats RAG (636 MB)",
        "model": "qllama/bge-reranker-v2-m3:latest",
        "category": "embedding",
        "local": True,
        "chat": False,
    },
}

MODEL_CATEGORIES = {
    "auto": {"label": "🎯 Auto", "order": 0},
    "cloud": {"label": "☁️ Cloud (Rapide)", "order": 1},
    "code": {"label": "💻 Code (Local)", "order": 2},
    "vision": {"label": "👁️ Vision (Local)", "order": 3},
    "security": {"label": "🛡️ Sécurité (Local)", "order": 4},
    "embedding": {"label": "📊 Embeddings (RAG)", "order": 5},
}

DEFAULT_MODEL = "qwen3-coder:480b-cloud"

# ===== DÉFINITION DES OUTILS =====

if TOOLS_MODULE_ENABLED:
    from tools import TOOLS_DEFINITIONS

    # Convertir en format dict pour compatibilité
    TOOLS = {}
    for t in TOOLS_DEFINITIONS:
        params = t.get("parameters", {})
        example_args = ", ".join([f'{k}="..."' for k in params.keys()])
        TOOLS[t["name"]] = {
            "description": t["description"],
            "parameters": params,
            "example": f"{t['name']}({example_args})",
        }
else:
    # Fallback minimal
    TOOLS = {
        "final_answer": {
            "description": "Réponse finale",
            "parameters": {"answer": "str"},
            "example": 'final_answer(answer="...")',
        }
    }

# ===== BASE DE DONNÉES =====


def init_db():
    """Initialiser la base SQLite"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Table conversations avec historique complet
    c.execute("""CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        title TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # Table messages
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT,
        role TEXT,
        content TEXT,
        model_used TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id)
    )""")

    # Table mémoire
    c.execute("""CREATE TABLE IF NOT EXISTS memory (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # Table fichiers uploadés
    c.execute("""CREATE TABLE IF NOT EXISTS uploads (
        id TEXT PRIMARY KEY,
        filename TEXT,
        filepath TEXT,
        filetype TEXT,
        filesize INTEGER,
        conversation_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()
    conn.close()


def get_db():
    """Obtenir une connexion DB"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ===== SÉLECTION AUTOMATIQUE DE MODÈLE =====


def auto_select_model(message: str, has_image: bool = False) -> str:
    """Toujours utiliser le modele cloud sauf pour les images"""
    if has_image:
        return MODELS["llama-vision"]["model"]
    return DEFAULT_MODEL


# ===== GESTION DES FICHIERS =====


async def save_upload(file: UploadFile, conversation_id: str = None) -> dict:
    """Sauvegarder un fichier uploadé"""
    file_id = str(uuid.uuid4())[:8]

    # Déterminer le type
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()

    if ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]:
        filetype = "image"
    elif ext in [".txt", ".md", ".json", ".yaml", ".yml", ".log", ".csv"]:
        filetype = "text"
    elif ext in [".py", ".js", ".ts", ".sh", ".bash", ".php", ".html", ".css"]:
        filetype = "code"
    else:
        filetype = "binary"

    # Sauvegarder le fichier
    filepath = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
    content = await file.read()

    with open(filepath, "wb") as f:
        f.write(content)

    # Enregistrer en DB
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """INSERT INTO uploads (id, filename, filepath, filetype, filesize, conversation_id)
                 VALUES (?, ?, ?, ?, ?, ?)""",
        (file_id, filename, filepath, filetype, len(content), conversation_id),
    )
    conn.commit()
    conn.close()

    return {"id": file_id, "filename": filename, "filetype": filetype, "size": len(content)}


def get_upload_info(file_id: str) -> dict:
    """Récupérer les infos d'un fichier uploadé"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM uploads WHERE id = ?", (file_id,))
    row = c.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def get_file_content(file_id: str) -> tuple:
    """Récupérer le contenu d'un fichier (content, filetype)"""
    info = get_upload_info(file_id)
    if not info:
        return None, None

    filepath = info["filepath"]
    filetype = info["filetype"]

    if filetype == "image":
        with open(filepath, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")
        return content, "image"
    else:
        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
            return content, "text"
        except:
            with open(filepath, "rb") as f:
                content = f.read().hex()
            return content, "binary"


# ===== GESTION HISTORIQUE =====


def create_conversation(title: str = None) -> str:
    """Créer une nouvelle conversation"""
    conv_id = str(uuid.uuid4())[:12]
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO conversations (id, title) VALUES (?, ?)",
        (conv_id, title or f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"),
    )
    conn.commit()
    conn.close()
    return conv_id


def add_message(conversation_id: str, role: str, content: str, model_used: str = None):
    """Ajouter un message à une conversation - P0-1: Validation anti-vide"""
    # P0-BUG FIX: Validation des types pour éviter erreur SQLite
    if not isinstance(conversation_id, str):
        logger.error(
            f"❌ add_message: conversation_id invalide (type={type(conversation_id)}, val={conversation_id})"
        )
        raise ValueError(f"conversation_id doit être une string, pas {type(conversation_id)}")
    if not isinstance(role, str):
        logger.error(f"❌ add_message: role invalide (type={type(role)})")
        raise ValueError(f"role doit être une string, pas {type(role)}")
    if not isinstance(content, str):
        logger.warning(f"⚠️ add_message: content converti en string (type={type(content)})")
        import json

        content = (
            json.dumps(content, ensure_ascii=False)
            if isinstance(content, (dict, list))
            else str(content)
            if content
            else ""
        )
    if model_used is not None and not isinstance(model_used, str):
        logger.warning(f"⚠️ add_message: model_used converti en string (type={type(model_used)})")
        model_used = str(model_used)

    # P0-1 FIX: Refuser les réponses vides pour role=assistant
    if role == "assistant" and (not content or not content.strip()):
        logger.warning(
            f"⚠️ P0-1: Tentative de sauvegarde réponse vide bloquée (conv={conversation_id})"
        )
        content = "❌ Erreur: Impossible de générer une réponse. Veuillez reformuler votre demande."

    conn = get_db()
    c = conn.cursor()
    c.execute(
        """INSERT INTO messages (conversation_id, role, content, model_used)
                 VALUES (?, ?, ?, ?)""",
        (conversation_id, role, content, model_used),
    )
    c.execute(
        "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (conversation_id,)
    )
    conn.commit()
    conn.close()

    # P0-1 FIX: Log pour traçabilité
    if role == "assistant":
        logger.debug(
            f"✅ Message assistant sauvegardé (conv={conversation_id}, len={len(content)})"
        )


def get_conversations(limit: int = 20) -> list:
    """Récupérer les conversations récentes"""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """SELECT c.*,
                 (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY created_at LIMIT 1) as first_message
                 FROM conversations c
                 ORDER BY updated_at DESC LIMIT ?""",
        (limit,),
    )
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_conversation_messages(conversation_id: str) -> list:
    """Récupérer les messages d'une conversation"""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at", (conversation_id,)
    )
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_conversation_title(conversation_id: str, title: str):
    """Mettre à jour le titre d'une conversation"""
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, conversation_id))
    conn.commit()
    conn.close()


def delete_conversation(conversation_id: str):
    """Supprimer une conversation, ses messages et les fichiers uploadés"""
    conn = get_db()
    c = conn.cursor()

    # 1. Récupérer les chemins des fichiers à supprimer
    c.execute("SELECT filepath FROM uploads WHERE conversation_id = ?", (conversation_id,))
    files_to_delete = [row[0] for row in c.fetchall()]

    # 2. Supprimer les entrées DB
    c.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    c.execute("DELETE FROM uploads WHERE conversation_id = ?", (conversation_id,))
    c.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    conn.commit()
    conn.close()

    # 3. Supprimer les fichiers physiques
    import os

    for filepath in files_to_delete:
        try:
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"🗑️ Fichier supprimé: {filepath}")
        except Exception as e:
            logger.warning(f"⚠️ Erreur suppression {filepath}: {e}")


# ===== EXÉCUTION DES OUTILS =====


async def execute_tool(tool_name: str, params: dict, uploaded_files: dict = None) -> str:
    """
    Exécuter un outil - Version v4.0 STRICTE
    Dispatch vers tools/ pour les outils async sécurisés.
    Plus de fallback legacy.
    """

    if not TOOLS_MODULE_ENABLED:
        return "❌ ERREUR CRITIQUE: Le module tools v4.0 n'est pas chargé. Impossible d'exécuter l'outil."

    try:
        # Préparer les validateurs de sécurité
        security_validator = None
        audit_logger_instance = None

        if SECURITY_ENABLED:
            security_validator = validate_command
            audit_logger_instance = audit_log

        result = await tools_execute_tool(
            tool_name,
            params,
            uploaded_files=uploaded_files,
            security_validator=security_validator,
            audit_logger=audit_logger_instance,
        )
        return result
    except Exception as e:
        print(f"⚠️ Erreur module tools v4.0: {e}")
        return f"Erreur lors de l'exécution de {tool_name}: {str(e)}"


# ===== MOTEUR REACT =====
from engine import react_loop

# ===== APPLICATION FASTAPI =====


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialisation au démarrage"""
    init_db()

    # Initialiser la base d'authentification
    if AUTH_ENABLED:
        try:
            init_auth_db()
            logger.info("✅ Base d'authentification initialisée")
        except Exception as e:
            logger.error(f"⚠️ Erreur init auth DB: {e}")

    # Démarrer la tâche de nettoyage du rate limiter
    if RATE_LIMIT_ENABLED:
        asyncio.create_task(cleanup_task())
        logger.info("✅ Rate limiter démarré")

    # Démarrer le Self-Healing Service
    if SELF_HEALING_ENABLED:
        asyncio.create_task(self_healing_service.start())

    yield


app = FastAPI(
    title="Orchestrateur IA 4LB.ca",
    description="Agent autonome avec boucle ReAct",
    version="2.0.0",
    lifespan=lifespan,
)

# Configuration CORS sécurisée
if CONFIG_ENABLED:
    cors_config = get_cors_config()
    app.add_middleware(CORSMiddleware, **cors_config)
else:
    # Fallback: CORS restrictif par défaut
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://ai.4lb.ca", "https://4lb.ca", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

# Rate Limiting middleware
if RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)

# ===== MODÈLES PYDANTIC =====


class ChatRequest(BaseModel):
    message: str
    model: str = "auto"
    conversation_id: str | None = None
    file_ids: list[str] | None = None


class ConversationUpdate(BaseModel):
    title: str


# ===== ENDPOINTS API =====


@app.get("/api/status")
async def root():
    return {"status": "ok", "service": "AI Orchestrator v3.0", "tools": len(TOOLS)}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "3.0.0",
        "tools_count": len(TOOLS),
        "models_count": len(MODELS),
        "ollama_url": OLLAMA_URL,
        "security_enabled": SECURITY_ENABLED,
        "auth_enabled": AUTH_ENABLED,
        "rate_limit_enabled": RATE_LIMIT_ENABLED,
    }


# ===== ENDPOINTS D'AUTHENTIFICATION v3.0 =====


@app.post("/api/auth/login", response_model=Token if AUTH_ENABLED else None)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """Authentification et obtention d'un token JWT"""
    if not AUTH_ENABLED:
        raise HTTPException(status_code=501, detail="Authentication not enabled")

    ip = request.client.host if request.client else "unknown"

    # Rate limiting pour les tentatives de login
    if not check_login_rate_limit(form_data.username, ip):
        raise HTTPException(
            status_code=429, detail="Too many login attempts. Try again in 15 minutes."
        )

    # Authentification
    user = authenticate_user(form_data.username, form_data.password)
    record_login_attempt(form_data.username, ip, success=user is not None)

    if SECURITY_ENABLED:
        audit_log.log_auth(form_data.username, success=user is not None, ip=ip)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if user.disabled:
        raise HTTPException(status_code=403, detail="Account disabled")

    # Créer les tokens
    access_token = create_access_token(data={"sub": user.username, "scopes": user.scopes})
    # Obtenir le vrai user_id
    user_id = get_user_id(user.username) or 1
    refresh_token = create_refresh_token(
        user_id=user_id, ip_address=ip, user_agent=request.headers.get("User-Agent", "")
    )

    return Token(
        access_token=access_token, refresh_token=refresh_token, token_type="bearer", expires_in=3600
    )


@app.post("/api/auth/refresh")
async def refresh_token_endpoint(refresh_token: str):
    """Renouveler un token d'accès"""
    if not AUTH_ENABLED:
        raise HTTPException(status_code=501, detail="Authentication not enabled")

    user_id = verify_refresh_token(refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Récupérer l'utilisateur par son ID
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token(data={"sub": user.username, "scopes": user.scopes})

    return {"access_token": access_token, "token_type": "bearer", "expires_in": 3600}


@app.post("/api/auth/logout")
async def logout(refresh_token: str):
    """Révoquer un refresh token"""
    if not AUTH_ENABLED:
        raise HTTPException(status_code=501, detail="Authentication not enabled")

    revoke_refresh_token(refresh_token)
    return {"message": "Logged out successfully"}


@app.get("/api/auth/me")
async def get_me(current_user=Depends(get_current_active_user) if AUTH_ENABLED else None):
    """Obtenir les informations de l'utilisateur courant"""
    if not AUTH_ENABLED:
        return {"username": "anonymous", "scopes": ["admin"]}
    return current_user


@app.post("/api/auth/users")
async def create_new_user(
    user_data: UserCreate, current_user=Depends(get_current_admin_user) if AUTH_ENABLED else None
):
    """Créer un nouvel utilisateur (admin requis)"""
    if not AUTH_ENABLED:
        raise HTTPException(status_code=501, detail="Authentication not enabled")
    return create_user(user_data)


@app.post("/api/auth/apikeys")
async def create_new_api_key(
    name: str,
    scopes: list[str],
    expires_days: int | None = None,
    current_user=Depends(get_current_admin_user) if AUTH_ENABLED else None,
):
    """Créer une nouvelle API key (admin requis)"""
    if not AUTH_ENABLED:
        raise HTTPException(status_code=501, detail="Authentication not enabled")

    key = create_api_key(name, user_id=1, scopes=scopes, expires_days=expires_days)
    return {"key": key, "name": name, "scopes": scopes}


@app.get("/api/security/config")
async def get_security_config_endpoint(
    current_user=Depends(get_current_admin_user) if AUTH_ENABLED else None,
):
    """Obtenir la configuration de sécurité (admin requis)"""
    if not SECURITY_ENABLED:
        return {"error": "Security module not enabled"}
    return get_security_config()


@app.get("/api/security/rate-limit-stats")
async def get_rate_limit_stats_endpoint(
    current_user=Depends(get_current_admin_user) if AUTH_ENABLED else None,
):
    """Obtenir les statistiques de rate limiting (admin requis)"""
    if not RATE_LIMIT_ENABLED:
        return {"error": "Rate limiting not enabled"}
    return await get_rate_limit_stats()


@app.get("/api/models")
async def list_models():
    """Liste des modèles disponibles avec catégories"""
    models_by_category = {}

    for model_id, model_data in MODELS.items():
        category = model_data.get("category", "other")
        if category not in models_by_category:
            models_by_category[category] = []

        # Exclure les modèles embedding du sélecteur de chat
        if model_data.get("chat", True) is False:
            continue

        models_by_category[category].append({
            "id": model_id,
            "name": model_data["name"],
            "description": model_data["description"],
            "category": category,
            "local": model_data.get("local", True),
        })

    return {
        "models": [
            {"id": k, "name": v["name"], "description": v["description"], "category": v.get("category", "other")}
            for k, v in MODELS.items() if v.get("chat", True) is not False
        ],
        "categories": MODEL_CATEGORIES,
        "models_by_category": models_by_category,
        "default": "auto",
    }


@app.get("/tools")
async def list_tools():
    """Liste des outils disponibles (dynamique)"""
    if TOOLS_MODULE_ENABLED:
        from tools import get_tool_count, get_tools_definitions

        tools_list = get_tools_definitions()
        return {
            "tools": [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t.get("parameters", {}),
                }
                for t in tools_list
            ],
            "count": get_tool_count(),
        }
    return {"tools": [], "count": 0}


@app.post("/api/tools/reload")
async def reload_tools_endpoint(
    current_user=Depends(get_current_admin_user) if AUTH_ENABLED else None,
):
    """Recharger les outils à chaud (admin requis) - pour l'auto-amélioration"""
    if not TOOLS_MODULE_ENABLED:
        raise HTTPException(status_code=501, detail="Tools module not enabled")

    from tools import reload_tools

    result = reload_tools()

    logger.info(f"🔄 Outils rechargés: {result['tools_count']} outils")

    return {
        "success": True,
        "tools_count": result["tools_count"],
        "modules": result["modules_loaded"],
        "tools": result["tools"],
    }


@app.get("/api/stats")
async def get_system_stats():
    """Get real-time system stats for dashboard"""
    import subprocess

    stats = {
        "cpu": {"percent": 0, "cores": 0},
        "memory": {"used_gb": 0, "total_gb": 0, "percent": 0},
        "gpu": {"name": "N/A", "memory_used": 0, "memory_total": 0, "percent": 0},
        "docker": {"running": 0, "total": 0},
    }

    try:
        # CPU usage
        cpu_result = subprocess.run(
            ["sh", "-c", "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        stats["cpu"]["percent"] = round(float(cpu_result.stdout.strip() or 0), 1)

        cores_result = subprocess.run(["nproc"], capture_output=True, text=True, timeout=5)
        stats["cpu"]["cores"] = int(cores_result.stdout.strip() or 0)

        # Memory
        mem_result = subprocess.run(
            ["sh", "-c", "free -b | awk '/^Mem:/ {print $2, $3}'"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if mem_result.stdout.strip():
            parts = mem_result.stdout.strip().split()
            if len(parts) >= 2:
                total, used = int(parts[0]), int(parts[1])
                stats["memory"]["total_gb"] = round(total / (1024**3), 1)
                stats["memory"]["used_gb"] = round(used / (1024**3), 1)
                stats["memory"]["percent"] = round((used / total) * 100, 1)

        # GPU (read from host file)
        try:
            with open("/tmp/gpu-stats.txt") as f:
                gpu_data = f.read().strip()
            if gpu_data:
                parts = gpu_data.split(", ")
                if len(parts) >= 4:
                    stats["gpu"]["name"] = parts[0]
                    stats["gpu"]["memory_used"] = int(parts[1])
                    stats["gpu"]["memory_total"] = int(parts[2])
                    stats["gpu"]["percent"] = int(parts[3])
        except FileNotFoundError:
            pass

        # Docker
        docker_result = subprocess.run(
            ["sh", "-c", "docker ps -q 2>/dev/null | wc -l"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        stats["docker"]["running"] = int(docker_result.stdout.strip() or 0)

        docker_all = subprocess.run(
            ["sh", "-c", "docker ps -aq 2>/dev/null | wc -l"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        stats["docker"]["total"] = int(docker_all.stdout.strip() or 0)

    except Exception as e:
        stats["error"] = str(e)

    return stats


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), conversation_id: str | None = Form(None)):
    """Upload un fichier"""
    try:
        result = await save_upload(file, conversation_id)
        return {"success": True, "file": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(
    request: ChatRequest, current_user=Depends(get_current_active_user) if AUTH_ENABLED else None
):
    """Endpoint chat synchrone"""
    # Déterminer le modèle
    has_image = False
    uploaded_files = []

    # P0-BUG FIX: Validation file_ids
    if request.file_ids and isinstance(request.file_ids, list):
        for fid in request.file_ids:
            info = get_upload_info(fid)
            if info:
                uploaded_files.append(info)
                if info["filetype"] == "image":
                    has_image = True

    if request.model == "auto":
        model = auto_select_model(request.message, has_image)
    else:
        model = MODELS.get(request.model, {}).get("model", DEFAULT_MODEL)

    # Créer ou utiliser une conversation
    conv_id = request.conversation_id or create_conversation()

    # Sauvegarder le message utilisateur
    add_message(conv_id, "user", request.message)

    # Exécuter la boucle ReAct
    response = await react_loop(
        user_message=request.message,
        model=model,
        conversation_id=conv_id,
        execute_tool_func=execute_tool,
        uploaded_files=uploaded_files,
    )

    # Sauvegarder la réponse
    add_message(conv_id, "assistant", response, model)

    # Mettre à jour le titre si c'est le premier message
    messages = get_conversation_messages(conv_id)
    if len(messages) <= 2:
        title = request.message[:50] + "..." if len(request.message) > 50 else request.message
        update_conversation_title(conv_id, title)

    return {"response": response, "conversation_id": conv_id, "model_used": model}


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, token: str = Query(None)):
    """WebSocket pour chat en temps réel (authentification requise si AUTH_ENABLED)"""

    # Vérification du token si AUTH_ENABLED
    if AUTH_ENABLED:
        if not token:
            await websocket.accept()
            await websocket.close(code=4001, reason="Token required")
            return

        token_data = verify_token(token)
        if not token_data:
            await websocket.accept()
            await websocket.close(code=4001, reason="Invalid token")
            return

    await websocket.accept()

    conv_id = None  # Initialiser pour éviter UnboundLocalError

    try:
        while True:
            data = await websocket.receive_json()

            message = data.get("message", "")
            model_key = data.get("model", "auto")
            conv_id = data.get("conversation_id")
            file_ids = data.get("file_ids", [])

            # P0-BUG FIX: Validation des types pour éviter erreur SQLite
            if conv_id is not None and not isinstance(conv_id, str):
                logger.warning(f"⚠️ conv_id invalide (type={type(conv_id)}), reset to None")
                conv_id = None
            if file_ids and not isinstance(file_ids, list):
                logger.warning(f"⚠️ file_ids invalide (type={type(file_ids)}), reset to []")
                file_ids = []

            # Traiter les fichiers
            has_image = False
            uploaded_files = []
            if file_ids:
                for fid in file_ids:
                    info = get_upload_info(fid)
                    if info:
                        uploaded_files.append(info)
                        if info["filetype"] == "image":
                            has_image = True

            # Sélection du modèle
            if model_key == "auto":
                model = auto_select_model(message, has_image)
                await websocket.send_json(
                    {
                        "type": "model_selected",
                        "model": model,
                        "reason": "image attachée" if has_image else "analyse automatique",
                    }
                )
            else:
                model = MODELS.get(model_key, {}).get("model", DEFAULT_MODEL)

            # Créer conversation si nécessaire
            if not conv_id:
                conv_id = create_conversation()
                await websocket.send_json(
                    {"type": "conversation_created", "conversation_id": conv_id}
                )

            # Sauvegarder message utilisateur
            add_message(conv_id, "user", message)

            # 🧠 AUTO-APPRENTISSAGE: Extraire et mémoriser les faits
            learned_facts = []
            if AUTO_LEARN_ENABLED:
                try:
                    learned_facts = auto_learn_from_message(message, conv_id)
                    if learned_facts:
                        await websocket.send_json(
                            {
                                "type": "activity",
                                "action": f"🧠 Auto-apprentissage: {len(learned_facts)} fait(s) mémorisé(s)",
                                "details": ", ".join(learned_facts),
                            }
                        )
                except Exception as e:
                    print(f"Erreur auto-learn: {e}")

            # 🔍 Charger le contexte pertinent
            relevant_context = []
            if AUTO_LEARN_ENABLED:
                try:
                    relevant_context = get_relevant_context(message, limit=3)
                except Exception as e:
                    print(f"Erreur context: {e}")

            # Exécuter la boucle ReAct avec contexte
            context_enhanced_message = message
            if relevant_context:
                context_str = "\n".join(relevant_context)
                context_enhanced_message = (
                    f"[CONTEXTE MÉMOIRE]\n{context_str}\n[/CONTEXTE]\n\n{message}"
                )

            response = await react_loop(
                user_message=context_enhanced_message,
                model=model,
                conversation_id=conv_id,
                execute_tool_func=execute_tool,
                uploaded_files=uploaded_files,
                websocket=websocket,
            )

            # Sauvegarder la réponse
            add_message(conv_id, "assistant", response, model)

    except WebSocketDisconnect:
        # Sauvegarder résumé de conversation à la déconnexion
        if AUTO_LEARN_ENABLED and conv_id:
            try:
                messages = get_conversation_messages(conv_id)
                if messages and len(messages) >= 2:
                    save_conversation_summary(messages, conv_id)
            except Exception as e:
                print(f"Erreur sauvegarde résumé: {e}")
    except Exception as e:
        import traceback

        logger.error(f"❌ WebSocket Error: {e}")
        logger.error(traceback.format_exc())
        import traceback as tb

        logger.error(f"WebSocket error details: {tb.format_exc()}")
        await websocket.send_json({"type": "error", "message": str(e)})


# ===== ENDPOINTS HISTORIQUE =====


@app.get("/api/conversations")
async def get_conversations_list(limit: int = 20):
    """Liste des conversations récentes"""
    return {"conversations": get_conversations(limit)}


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Détails d'une conversation"""
    messages = get_conversation_messages(conversation_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation non trouvée")
    return {"conversation_id": conversation_id, "messages": messages}


@app.put("/api/conversations/{conversation_id}")
async def update_conversation(conversation_id: str, update: ConversationUpdate):
    """Mettre à jour le titre d'une conversation"""
    update_conversation_title(conversation_id, update.title)
    return {"success": True}


@app.delete("/api/conversations/{conversation_id}")
async def delete_conv(conversation_id: str):
    """Supprimer une conversation"""
    delete_conversation(conversation_id)
    return {"success": True}


@app.get("/api/docker/status")
async def get_docker_status():
    """Statut des conteneurs Docker pour le frontend"""
    import json as json_module
    import subprocess

    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        containers = []
        for line in result.stdout.strip().split("\n"):
            if line:
                try:
                    c = json_module.loads(line)
                    containers.append(
                        {
                            "name": c.get("Names", "unknown"),
                            "status": c.get("Status", "unknown"),
                            "image": c.get("Image", ""),
                            "ports": c.get("Ports", ""),
                        }
                    )
                except:
                    pass
        return containers
    except Exception as e:
        logger.error(f"Erreur docker status: {e}")
        return []


# ===== ENDPOINTS MONITORING v5.1 =====


@app.get("/api/logs")
async def get_server_logs(
    lines: int = 100,
    level: str = None,
    current_user=Depends(get_current_admin_user) if AUTH_ENABLED else None,
):
    """Voir les dernières lignes des logs serveur (admin requis)"""
    try:
        with open("server.log") as f:
            all_lines = f.readlines()

        # Filtrer par niveau si spécifié
        if level:
            level = level.upper()
            all_lines = [l for l in all_lines if f"[{level}]" in l]

        # Retourner les N dernières lignes
        recent = all_lines[-lines:] if len(all_lines) > lines else all_lines

        return {
            "total_lines": len(all_lines),
            "returned": len(recent),
            "logs": [l.strip() for l in recent],
        }
    except FileNotFoundError:
        return {"error": "Log file not found", "logs": []}
    except Exception as e:
        return {"error": str(e), "logs": []}


@app.get("/api/system/status")
async def get_system_status():
    """Statut complet du système pour monitoring"""
    from tools import get_tool_count

    # Collecter les infos
    status = {"version": "5.1.0", "healthy": True, "components": {}}

    # Backend
    status["components"]["backend"] = {
        "status": "running",
        "tools_count": get_tool_count(),
        "auth_enabled": AUTH_ENABLED,
        "security_enabled": SECURITY_ENABLED,
        "self_healing_enabled": SELF_HEALING_ENABLED,
    }

    # Ollama
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            models = r.json().get("models", [])
            status["components"]["ollama"] = {
                "status": "connected",
                "url": OLLAMA_URL,
                "models_count": len(models),
            }
    except Exception as e:
        status["components"]["ollama"] = {"status": "error", "error": str(e)}
        status["healthy"] = False

    # ChromaDB
    try:
        client = get_chroma_client()
        if client:
            collections = client.list_collections()
            status["components"]["chromadb"] = {
                "status": "connected",
                "collections": len(collections),
            }
        else:
            status["components"]["chromadb"] = {"status": "not configured"}
    except Exception as e:
        status["components"]["chromadb"] = {"status": "error", "error": str(e)}

    # Docker
    try:
        result = subprocess.run(["docker", "ps", "-q"], capture_output=True, timeout=5)
        containers = len(result.stdout.decode().strip().split("\n")) if result.stdout else 0
        status["components"]["docker"] = {"status": "running", "containers": containers}
    except Exception as e:
        status["components"]["docker"] = {"status": "error", "error": str(e)}

    return status


# Servir le frontend
try:
    app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
except Exception as e:
    print(f"⚠️ Impossible de monter le frontend: {e}")

# ===== POINT D'ENTRÉE =====

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
