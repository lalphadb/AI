#!/usr/bin/env python3
"""
Orchestrateur IA 4LB.ca - Backend FastAPI v3.0
Agent autonome avec boucle ReAct, sélection auto de modèle, upload fichiers
Sécurité: JWT, Rate Limiting, Validation commandes/chemins
"""

import os
import json
import asyncio
import sqlite3
import httpx
import subprocess
import re
import base64
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form, Depends, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
import chromadb
from chromadb.config import Settings

# ===== MODULES DE SÉCURITÉ v3.0 =====
try:
    from security import (
        validate_command,
        validate_path,
        is_path_allowed,
        CommandNotAllowedError,
        PathNotAllowedError,
        audit_log,
        get_security_config,
    )
    SECURITY_ENABLED = True
except ImportError:
    SECURITY_ENABLED = False
    print("⚠️ Module security non disponible - Validation désactivée")

try:
    from auth import (
        get_current_user,
        verify_token,
        get_current_active_user,
        get_optional_user,
        get_current_admin_user,
        require_scope,
        create_access_token,
        create_refresh_token,
        verify_refresh_token,
        revoke_refresh_token,
        authenticate_user,
        create_user,
        update_user,
        get_user,
        check_login_rate_limit,
        record_login_attempt,
        create_api_key,
        init_auth_db,
        Token,
        User,
        UserCreate,
        UserUpdate,
        APIKey,
        AUTH_ENABLED,
    )
except ImportError:
    AUTH_ENABLED = False
    print("⚠️ Module auth non disponible - Authentification désactivée")

try:
    from rate_limiter import RateLimitMiddleware, rate_limiter, get_rate_limit_stats, cleanup_task
    RATE_LIMIT_ENABLED = True
except ImportError:
    RATE_LIMIT_ENABLED = False
    print("⚠️ Module rate_limiter non disponible - Rate limiting désactivé")

try:
    from config import get_settings, get_cors_config, MODELS as CONFIG_MODELS
    CONFIG_ENABLED = True
except ImportError:
    CONFIG_ENABLED = False
    print("⚠️ Module config non disponible - Configuration par défaut")

try:
    from prompts import build_system_prompt, get_urgency_message
    PROMPTS_ENABLED = True
except ImportError:
    PROMPTS_ENABLED = False
    print("⚠️ Module prompts non disponible - Prompts par défaut")

try:
    from dynamic_context import get_dynamic_context
    DYNAMIC_CONTEXT_ENABLED = True
except ImportError:
    DYNAMIC_CONTEXT_ENABLED = False
    print("⚠️ Module dynamic_context non disponible")

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
import os
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
        save_conversation_summary,
        get_relevant_context,
        get_user_preferences,
        get_memory_stats
    )
    AUTO_LEARN_ENABLED = True
except ImportError:
    AUTO_LEARN_ENABLED = False
    print("⚠️ Module auto_learn non disponible")

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
            metadata={"description": "Mémoire sémantique de l'AI Orchestrator"}
        )
    return None

MAX_ITERATIONS = 20

# Modèles disponibles avec leurs spécialités
MODELS = {
    "auto": {
        "name": "AUTO (Sélection automatique)",
        "description": "L'agent choisit le meilleur modèle selon la tâche",
        "model": None
    },
    # === MODÈLES LOCAUX ===
    "qwen-coder": {
        "name": "💻 Qwen 2.5 Coder 32B",
        "description": "Code, scripts, debug, analyse technique",
        "model": "qwen2.5-coder:32b-instruct-q4_K_M",
        "keywords": ["code", "script", "python", "bash", "debug", "fonction", "variable", "api", "docker", "git", "npm", "programm"]
    },
    "deepseek-coder": {
        "name": "🧠 DeepSeek Coder 33B",
        "description": "Code alternatif, algorithmes complexes",
        "model": "deepseek-coder:33b",
        "keywords": ["algorithme", "optimis", "complex", "performance", "refactor"]
    },
    "llama-vision": {
        "name": "👁️ Llama 3.2 Vision 11B",
        "description": "Analyse d'images, OCR, vision",
        "model": "llama3.2-vision:11b-instruct-q8_0",
        "keywords": ["image", "photo", "screenshot", "capture", "voir", "regarde", "analyse visuel", "ocr"]
    },
    "qwen-vision": {
        "name": "🎨 Qwen3 VL 32B",
        "description": "Vision multimodale avancée",
        "model": "qwen3-vl:32b",
        "keywords": ["image", "multimodal", "vision", "graphique", "diagramme", "schéma"]
    },
    # === MODÈLES CLOUD (via Ollama) ===
    "kimi-k2": {
        "name": "☁️ Kimi K2 1T",
        "description": "Modèle cloud Kimi (Moonshot AI)",
        "model": "kimi-k2:1t-cloud",
        "keywords": ["kimi", "moonshot", "cloud", "chinois"]
    },
    "qwen3-coder-cloud": {
        "name": "☁️ Qwen3 Coder 480B",
        "description": "Qwen3 Coder géant via cloud",
        "model": "qwen3-coder:480b-cloud",
        "keywords": ["qwen", "cloud", "coder", "gros"]
    },
    "gemini-pro": {
        "name": "☁️ Gemini 3 Pro",
        "description": "Google Gemini Pro via cloud",
        "model": "gemini-3-pro-preview:latest",
        "keywords": ["gemini", "google", "cloud"]
    },
    "gpt-safeguard": {
        "name": "🛡️ GPT Safeguard 13B",
        "description": "GPT Open Source local (sécurité)",
        "model": "gpt-oss-safeguard:latest",
        "keywords": ["gpt", "safeguard", "sécurité", "modération"]
    }
}

DEFAULT_MODEL = "qwen3-coder:480b-cloud"

# ===== DÉFINITION DES OUTILS =====

TOOLS = {
    "execute_command": {
        "description": "Exécuter une commande bash sur le serveur Ubuntu",
        "parameters": {"command": "string - La commande à exécuter"},
        "example": "execute_command(command=\"ls -la /home/lalpha\")"
    },
    "system_info": {
        "description": "Obtenir les informations système (CPU, RAM, disque, GPU)",
        "parameters": {},
        "example": "system_info()"
    },
    "docker_status": {
        "description": "Voir l'état de tous les conteneurs Docker",
        "parameters": {},
        "example": "docker_status()"
    },
    "docker_logs": {
        "description": "Voir les logs d'un conteneur Docker",
        "parameters": {"container": "string - Nom du conteneur", "lines": "int - Nombre de lignes (défaut: 50)"},
        "example": "docker_logs(container=\"traefik\", lines=100)"
    },
    "docker_restart": {
        "description": "Redémarrer un conteneur Docker",
        "parameters": {"container": "string - Nom du conteneur"},
        "example": "docker_restart(container=\"traefik\")"
    },
    "disk_usage": {
        "description": "Analyser l'utilisation du disque",
        "parameters": {"path": "string - Chemin à analyser (défaut: /)"},
        "example": "disk_usage(path=\"/home/lalpha\")"
    },
    "service_status": {
        "description": "Vérifier le statut d'un service systemd",
        "parameters": {"service": "string - Nom du service"},
        "example": "service_status(service=\"ollama\")"
    },
    "service_control": {
        "description": "Contrôler un service (start, stop, restart)",
        "parameters": {"service": "string - Nom du service", "action": "string - Action: start, stop, restart"},
        "example": "service_control(service=\"ollama\", action=\"restart\")"
    },
    "read_file": {
        "description": "Lire le contenu d'un fichier",
        "parameters": {"path": "string - Chemin du fichier"},
        "example": "read_file(path=\"/home/lalpha/projets/README.md\")"
    },
    "write_file": {
        "description": "Écrire du contenu dans un fichier",
        "parameters": {"path": "string - Chemin du fichier", "content": "string - Contenu à écrire"},
        "example": "write_file(path=\"/home/lalpha/test.txt\", content=\"Hello\")"
    },
    "list_directory": {
        "description": "Lister le contenu d'un répertoire",
        "parameters": {"path": "string - Chemin du répertoire"},
        "example": "list_directory(path=\"/home/lalpha/projets\")"
    },
    "search_files": {
        "description": "Rechercher des fichiers par nom ou contenu",
        "parameters": {"pattern": "string - Motif de recherche", "path": "string - Répertoire de recherche", "content": "bool - Chercher dans le contenu"},
        "example": "search_files(pattern=\"*.py\", path=\"/home/lalpha/projets\")"
    },
    "udm_status": {
        "description": "Obtenir le statut du UDM-Pro UniFi",
        "parameters": {},
        "example": "udm_status()"
    },
    "udm_network_info": {
        "description": "Informations réseau du UDM-Pro (VLANs, clients)",
        "parameters": {},
        "example": "udm_network_info()"
    },
    "udm_clients": {
        "description": "Liste des clients connectés au réseau",
        "parameters": {},
        "example": "udm_clients()"
    },
    "network_scan": {
        "description": "Scanner les ports ouverts du serveur",
        "parameters": {},
        "example": "network_scan()"
    },
    "ollama_list": {
        "description": "Lister les modèles Ollama installés",
        "parameters": {},
        "example": "ollama_list()"
    },
    "ollama_run": {
        "description": "Exécuter une requête sur un modèle Ollama spécifique",
        "parameters": {"model": "string - Nom du modèle", "prompt": "string - Prompt"},
        "example": "ollama_run(model=\"qwen2.5-coder:32b\", prompt=\"Hello\")"
    },
    "analyze_image": {
        "description": "Analyser une image uploadée avec le modèle vision",
        "parameters": {"image_id": "string - ID de l'image uploadée", "question": "string - Question sur l'image"},
        "example": "analyze_image(image_id=\"abc123\", question=\"Que vois-tu sur cette image?\")"
    },
    "analyze_file": {
        "description": "Analyser un fichier uploadé",
        "parameters": {"file_id": "string - ID du fichier uploadé"},
        "example": "analyze_file(file_id=\"abc123\")"
    },
    "create_script": {
        "description": "Créer un script bash exécutable",
        "parameters": {"path": "string - Chemin", "content": "string - Contenu du script"},
        "example": "create_script(path=\"/home/lalpha/scripts/test.sh\", content=\"#!/bin/bash\\necho OK\")"
    },
    "git_status": {
        "description": "Voir le statut git d'un répertoire",
        "parameters": {"path": "string - Chemin du repo"},
        "example": "git_status(path=\"/home/lalpha/projets/ai-tools\")"
    },
    "git_diff": {
        "description": "Voir les différences non commitées dans un repo git",
        "parameters": {"path": "string - Chemin du repo"},
        "example": "git_diff(path=\"/home/lalpha/projets/ai-tools\")"
    },
    "git_log": {
        "description": "Voir l historique des commits git",
        "parameters": {"path": "string - Chemin du repo", "n": "int - Nombre de commits (défaut: 10)"},
        "example": "git_log(path=\"/home/lalpha/projets/ai-tools\", n=20)"
    },
    "git_commit": {
        "description": "Commiter les changements avec un message",
        "parameters": {"path": "string - Chemin du repo", "message": "string - Message de commit", "add_all": "bool - Ajouter tous les fichiers (défaut: true)"},
        "example": "git_commit(path=\"/home/lalpha/projets/ai-tools\", message=\"feat: nouvelle fonctionnalité\")"
    },
    "git_branch": {
        "description": "Lister ou changer de branche git",
        "parameters": {"path": "string - Chemin du repo", "branch": "string - Nom de branche (optionnel, pour switch)"},
        "example": "git_branch(path=\"/home/lalpha/projets/ai-tools\")"
    },
    "git_pull": {
        "description": "Tirer les changements du remote",
        "parameters": {"path": "string - Chemin du repo"},
        "example": "git_pull(path=\"/home/lalpha/projets/ai-tools\")"
    },
    "memory_store": {
        "description": "IMPORTANT: Stocker une information importante en mémoire sémantique. Utilise cet outil pour mémoriser: les préférences utilisateur, les contextes de projets, les décisions importantes, les faits clés. La mémoire persiste entre les conversations!",
        "parameters": {"key": "string - Catégorie/sujet (ex: projet_actuel, preference, fait_important)", "value": "string - Information détaillée à mémoriser"},
        "example": "memory_store(key=\"utilisateur\", value=\"Lalpha travaille sur un homelab IA avec Ollama et ChromaDB\")"
    },
    "memory_recall": {
        "description": "IMPORTANT: Rechercher dans la mémoire sémantique. Utilise 'all' pour voir toutes les mémoires récentes, ou une question/mot-clé pour une recherche sémantique. TOUJOURS utiliser au début d'une conversation pour se rappeler du contexte!",
        "parameters": {"query": "string - 'all' pour tout voir, ou question/mot-clé pour recherche sémantique"},
        "example": "memory_recall(query=\"projets en cours\")"
    },
    "memory_stats": {
        "description": "Afficher les statistiques de la mémoire: nombre total de souvenirs, répartition par type (base, auto_learned, conversation_summary, solved_issue) et par catégorie (user_fact, project, preference, tech_fact)",
        "parameters": {},
        "example": "memory_stats()"
    },
    "web_request": {
        "description": "Faire une requête HTTP GET/POST",
        "parameters": {"url": "string - URL", "method": "string - GET ou POST", "data": "string - Données JSON pour POST"},
        "example": "web_request(url=\"http://localhost:8001/health\", method=\"GET\")"
    },
    "create_plan": {
        "description": "Créer un plan d'exécution détaillé pour une tâche complexe. Utilise cet outil AVANT d'exécuter des tâches multi-étapes.",
        "parameters": {"task": "string - Description complète de la tâche à planifier"},
        "example": "create_plan(task=\"Créer un site web avec pages accueil, services et contact\")"
    },
    "validate_step": {
        "description": "Valider qu'une étape du plan a été correctement exécutée",
        "parameters": {"step_description": "string - Ce qui devait être fait", "expected_result": "string - Résultat attendu"},
        "example": "validate_step(step_description=\"Créer le dossier\", expected_result=\"Dossier existe\")"
    },
    "final_answer": {
        "description": "Fournir la réponse finale à l'utilisateur",
        "parameters": {"answer": "string - La réponse complète et structurée"},
        "example": "final_answer(answer=\"Voici le résultat de l'analyse...\")"
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
    c.execute('''CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        title TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Table messages
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT,
        role TEXT,
        content TEXT,
        model_used TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id)
    )''')
    
    # Table mémoire
    c.execute('''CREATE TABLE IF NOT EXISTS memory (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Table fichiers uploadés
    c.execute('''CREATE TABLE IF NOT EXISTS uploads (
        id TEXT PRIMARY KEY,
        filename TEXT,
        filepath TEXT,
        filetype TEXT,
        filesize INTEGER,
        conversation_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
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
    
    if ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']:
        filetype = 'image'
    elif ext in ['.txt', '.md', '.json', '.yaml', '.yml', '.log', '.csv']:
        filetype = 'text'
    elif ext in ['.py', '.js', '.ts', '.sh', '.bash', '.php', '.html', '.css']:
        filetype = 'code'
    else:
        filetype = 'binary'
    
    # Sauvegarder le fichier
    filepath = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
    content = await file.read()
    
    with open(filepath, 'wb') as f:
        f.write(content)
    
    # Enregistrer en DB
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO uploads (id, filename, filepath, filetype, filesize, conversation_id)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (file_id, filename, filepath, filetype, len(content), conversation_id))
    conn.commit()
    conn.close()
    
    return {
        "id": file_id,
        "filename": filename,
        "filetype": filetype,
        "size": len(content)
    }

def get_upload_info(file_id: str) -> dict:
    """Récupérer les infos d'un fichier uploadé"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM uploads WHERE id = ?', (file_id,))
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
    
    filepath = info['filepath']
    filetype = info['filetype']
    
    if filetype == 'image':
        with open(filepath, 'rb') as f:
            content = base64.b64encode(f.read()).decode('utf-8')
        return content, 'image'
    else:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 'text'
        except:
            with open(filepath, 'rb') as f:
                content = f.read().hex()
            return content, 'binary'

# ===== GESTION HISTORIQUE =====

def create_conversation(title: str = None) -> str:
    """Créer une nouvelle conversation"""
    conv_id = str(uuid.uuid4())[:12]
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO conversations (id, title) VALUES (?, ?)',
              (conv_id, title or f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"))
    conn.commit()
    conn.close()
    return conv_id

def add_message(conversation_id: str, role: str, content: str, model_used: str = None):
    """Ajouter un message à une conversation"""
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO messages (conversation_id, role, content, model_used)
                 VALUES (?, ?, ?, ?)''', (conversation_id, role, content, model_used))
    c.execute('UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?',
              (conversation_id,))
    conn.commit()
    conn.close()

def get_conversations(limit: int = 20) -> list:
    """Récupérer les conversations récentes"""
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT c.*, 
                 (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY created_at LIMIT 1) as first_message
                 FROM conversations c 
                 ORDER BY updated_at DESC LIMIT ?''', (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_conversation_messages(conversation_id: str) -> list:
    """Récupérer les messages d'une conversation"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at', (conversation_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_conversation_title(conversation_id: str, title: str):
    """Mettre à jour le titre d'une conversation"""
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE conversations SET title = ? WHERE id = ?', (title, conversation_id))
    conn.commit()
    conn.close()

def delete_conversation(conversation_id: str):
    """Supprimer une conversation et ses messages"""
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM messages WHERE conversation_id = ?', (conversation_id,))
    c.execute('DELETE FROM uploads WHERE conversation_id = ?', (conversation_id,))
    c.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))
    conn.commit()
    conn.close()

# ===== EXÉCUTION DES OUTILS =====

async def execute_tool(tool_name: str, params: dict, uploaded_files: dict = None) -> str:
    """Exécuter un outil et retourner le résultat"""
    
    try:
        if tool_name == "execute_command":
            cmd = params.get("command", "")
            if not cmd:
                return "Erreur: commande vide"

            # Validation de sécurité v3.0
            if SECURITY_ENABLED:
                allowed, reason = validate_command(cmd)
                audit_log.log_command(cmd, allowed=allowed, reason=reason)
                if not allowed:
                    return f"🚫 Commande bloquée pour des raisons de sécurité: {reason}"

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            output = result.stdout or result.stderr or "(aucune sortie)"
            return f"Commande: {cmd}\nSortie:\n{output[:3000]}"
        
        elif tool_name == "system_info":
            cmds = {
                "hostname": "hostname",
                "uptime": "uptime",
                "cpu": "lscpu | head -20",
                "memory": "free -h",
                "disk": "df -h /",
                "gpu": "nvidia-smi --query-gpu=name,memory.total,memory.used,temperature.gpu --format=csv,noheader 2>/dev/null || echo 'Pas de GPU'",
                "load": "cat /proc/loadavg"
            }
            results = []
            for name, cmd in cmds.items():
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                results.append(f"=== {name.upper()} ===\n{r.stdout or r.stderr}")
            return "\n".join(results)
        
        elif tool_name == "docker_status":
            result = subprocess.run(
                "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'",
                shell=True, capture_output=True, text=True, timeout=30
            )
            return f"Conteneurs Docker:\n{result.stdout or result.stderr}"
        
        elif tool_name == "docker_logs":
            container = params.get("container", "")
            lines = params.get("lines", 50)
            if not container:
                return "Erreur: nom du conteneur requis"
            result = subprocess.run(
                f"docker logs --tail {lines} {container} 2>&1",
                shell=True, capture_output=True, text=True, timeout=30
            )
            return f"Logs de {container}:\n{result.stdout or result.stderr}"
        
        elif tool_name == "docker_restart":
            container = params.get("container", "")
            if not container:
                return "Erreur: nom du conteneur requis"
            result = subprocess.run(
                f"docker restart {container}",
                shell=True, capture_output=True, text=True, timeout=60
            )
            return f"Redémarrage de {container}: {result.stdout or result.stderr}"
        
        elif tool_name == "disk_usage":
            path = params.get("path", "/")
            result = subprocess.run(
                f"du -sh {path}/* 2>/dev/null | sort -rh | head -20",
                shell=True, capture_output=True, text=True, timeout=30
            )
            df_result = subprocess.run(f"df -h {path}", shell=True, capture_output=True, text=True, timeout=10)
            return f"Espace disque:\n{df_result.stdout}\n\nDétail:\n{result.stdout}"
        
        elif tool_name == "service_status":
            service = params.get("service", "")
            if not service:
                return "Erreur: nom du service requis"
            result = subprocess.run(
                f"systemctl status {service} --no-pager",
                shell=True, capture_output=True, text=True, timeout=10
            )
            return f"Statut de {service}:\n{result.stdout or result.stderr}"
        
        elif tool_name == "service_control":
            service = params.get("service", "")
            action = params.get("action", "")
            if not service or action not in ["start", "stop", "restart"]:
                return "Erreur: service et action (start/stop/restart) requis"
            result = subprocess.run(
                f"sudo systemctl {action} {service}",
                shell=True, capture_output=True, text=True, timeout=30
            )
            return f"Action {action} sur {service}: {result.stdout or result.stderr or 'OK'}"
        
        elif tool_name == "read_file":
            path = params.get("path", "")
            if not path:
                return "Erreur: chemin requis"

            # Validation de sécurité v3.0
            if SECURITY_ENABLED:
                try:
                    path = validate_path(path, write=False)
                    audit_log.log_file_access(path, "read", allowed=True)
                except PathNotAllowedError as e:
                    audit_log.log_file_access(path, "read", allowed=False, reason=str(e))
                    return f"🚫 Accès refusé: {e}"

            if not os.path.exists(path):
                return f"Erreur: fichier non trouvé: {path}"
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read(10000)
                return f"Contenu de {path}:\n{content}"
            except Exception as e:
                return f"Erreur lecture: {e}"
        
        elif tool_name == "write_file":
            path = params.get("path", "")
            content = params.get("content", "")
            if not path:
                return "Erreur: chemin requis"

            # Validation de sécurité v3.0
            if SECURITY_ENABLED:
                try:
                    path = validate_path(path, write=True)
                    audit_log.log_file_access(path, "write", allowed=True)
                except PathNotAllowedError as e:
                    audit_log.log_file_access(path, "write", allowed=False, reason=str(e))
                    return f"🚫 Accès refusé: {e}"

            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return f"Fichier écrit: {path} ({len(content)} caractères)"
            except Exception as e:
                return f"Erreur écriture: {e}"
        
        elif tool_name == "list_directory":
            path = params.get("path", "/home/lalpha")
            if not os.path.exists(path):
                return f"Erreur: répertoire non trouvé: {path}"
            result = subprocess.run(
                f"ls -la {path}",
                shell=True, capture_output=True, text=True, timeout=10
            )
            return f"Contenu de {path}:\n{result.stdout}"
        
        elif tool_name == "search_files":
            pattern = params.get("pattern", "*")
            path = params.get("path", "/home/lalpha")
            content_search = params.get("content", False)
            if content_search:
                result = subprocess.run(
                    f"grep -r '{pattern}' {path} 2>/dev/null | head -50",
                    shell=True, capture_output=True, text=True, timeout=30
                )
            else:
                result = subprocess.run(
                    f"find {path} -name '{pattern}' 2>/dev/null | head -50",
                    shell=True, capture_output=True, text=True, timeout=30
                )
            return f"Recherche '{pattern}':\n{result.stdout or 'Aucun résultat'}"
        
        elif tool_name == "udm_status":
            result = subprocess.run(
                "ssh -i /home/lalpha/.ssh/id_rsa_udm -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@10.10.10.1 'uptime; echo; cat /etc/version; echo; df -h /'",
                shell=True, capture_output=True, text=True, timeout=15
            )
            return f"UDM-Pro Status:\n{result.stdout or result.stderr}"
        
        elif tool_name == "udm_network_info":
            result = subprocess.run(
                "ssh -i /home/lalpha/.ssh/id_rsa_udm -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@10.10.10.1 'ip addr show; echo; cat /run/dnsmasq.conf.d/*.conf 2>/dev/null | head -50'",
                shell=True, capture_output=True, text=True, timeout=15
            )
            return f"UDM-Pro Network:\n{result.stdout or result.stderr}"
        
        elif tool_name == "udm_clients":
            result = subprocess.run(
                "ssh -i /home/lalpha/.ssh/id_rsa_udm -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@10.10.10.1 'cat /proc/net/arp'",
                shell=True, capture_output=True, text=True, timeout=15
            )
            return f"Clients connectés:\n{result.stdout or result.stderr}"
        
        elif tool_name == "network_scan":
            result = subprocess.run(
                "ss -tlnp | head -30",
                shell=True, capture_output=True, text=True, timeout=10
            )
            return f"Ports ouverts:\n{result.stdout}"
        
        elif tool_name == "ollama_list":
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{OLLAMA_URL}/api/tags", timeout=10)
                data = resp.json()
                models = [f"- {m['name']} ({m.get('size', 'N/A')})" for m in data.get('models', [])]
                return f"Modèles Ollama:\n" + "\n".join(models)
        
        elif tool_name == "ollama_run":
            model = params.get("model", DEFAULT_MODEL)
            prompt = params.get("prompt", "")
            if not prompt:
                return "Erreur: prompt requis"
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False},
                    timeout=120
                )
                data = resp.json()
                return f"Réponse de {model}:\n{data.get('response', 'Erreur')}"
        
        elif tool_name == "analyze_image":
            image_id = params.get("image_id", "")
            question = params.get("question", "Décris cette image en détail")
            
            content, ftype = get_file_content(image_id)
            if not content or ftype != 'image':
                return f"Erreur: image non trouvée ou invalide: {image_id}"
            
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": MODELS["llama-vision"]["model"],
                        "prompt": question,
                        "images": [content],
                        "stream": False
                    },
                    timeout=180
                )
                data = resp.json()
                return f"Analyse de l'image:\n{data.get('response', 'Erreur analyse')}"
        
        elif tool_name == "analyze_file":
            file_id = params.get("file_id", "")
            content, ftype = get_file_content(file_id)
            if not content:
                return f"Erreur: fichier non trouvé: {file_id}"
            
            info = get_upload_info(file_id)
            if ftype == 'image':
                return f"C'est une image ({info['filename']}). Utilise analyze_image() pour l'analyser."
            else:
                preview = content[:5000] if len(content) > 5000 else content
                return f"Fichier: {info['filename']}\nType: {ftype}\nTaille: {info['filesize']} bytes\n\nContenu:\n{preview}"
        
        elif tool_name == "create_script":
            path = params.get("path", "")
            content = params.get("content", "")
            if not path or not content:
                return "Erreur: path et content requis"
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w') as f:
                    f.write(content)
                os.chmod(path, 0o755)
                return f"Script créé: {path} (exécutable)"
            except Exception as e:
                return f"Erreur création script: {e}"
        
        elif tool_name == "git_status":
            path = params.get("path", "/home/lalpha/projets")
            result = subprocess.run(
                f"cd {path} && git status && git log --oneline -5",
                shell=True, capture_output=True, text=True, timeout=10
            )
            return f"Git status de {path}:\n{result.stdout or result.stderr}"
        elif tool_name == "git_diff":
            path = params.get("path", "/home/lalpha/projets")
            result = subprocess.run(
                f"cd {path} && git diff --stat && echo '\n=== Détails ===' && git diff",
                shell=True, capture_output=True, text=True, timeout=30
            )
            output = result.stdout or result.stderr
            if not output.strip():
                return f"Aucune modification dans {path}"
            return f"Git diff de {path}:\n{output[:3000]}"
        
        elif tool_name == "git_log":
            path = params.get("path", "/home/lalpha/projets")
            n = params.get("n", 10)
            result = subprocess.run(
                f"cd {path} && git log --oneline --graph -n {n}",
                shell=True, capture_output=True, text=True, timeout=10
            )
            return f"Git log de {path} ({n} derniers commits):\n{result.stdout or result.stderr}"
        
        elif tool_name == "git_commit":
            path = params.get("path", "/home/lalpha/projets")
            message = params.get("message", "")
            add_all = params.get("add_all", True)
            if not message:
                return "Erreur: message de commit requis"
            add_cmd = "git add -A && " if add_all else ""
            result = subprocess.run(
                f'cd {path} && {add_cmd}git commit -m "{message}"',
                shell=True, capture_output=True, text=True, timeout=30
            )
            return f"Git commit dans {path}:\n{result.stdout or result.stderr}"
        
        elif tool_name == "git_branch":
            path = params.get("path", "/home/lalpha/projets")
            branch = params.get("branch", "")
            if branch:
                result = subprocess.run(
                    f"cd {path} && git checkout {branch}",
                    shell=True, capture_output=True, text=True, timeout=10
                )
                return f"Switch vers branche {branch}:\n{result.stdout or result.stderr}"
            else:
                result = subprocess.run(
                    f"cd {path} && git branch -a",
                    shell=True, capture_output=True, text=True, timeout=10
                )
                return f"Branches dans {path}:\n{result.stdout or result.stderr}"
        
        elif tool_name == "git_pull":
            path = params.get("path", "/home/lalpha/projets")
            result = subprocess.run(
                f"cd {path} && git pull",
                shell=True, capture_output=True, text=True, timeout=60
            )
            return f"Git pull dans {path}:\n{result.stdout or result.stderr}"

        
        elif tool_name == "memory_store":
            key = params.get("key", "")
            value = params.get("value", "")
            if not key:
                return "Erreur: clé requise"
            try:
                # ChromaDB - mémoire sémantique
                chroma_client = chromadb.HttpClient(host="chromadb", port=8000, settings=Settings(anonymized_telemetry=False))
                collection = chroma_client.get_or_create_collection(
                    name="ai_orchestrator_memory",
                    metadata={"description": "Mémoire sémantique de l'AI Orchestrator"}
                )
                # Upsert avec le document formaté
                doc_content = f"{key}: {value}"
                collection.upsert(
                    documents=[doc_content],
                    ids=[f"mem_{key}"],
                    metadatas=[{"key": key, "type": "user", "timestamp": datetime.now().isoformat()}]
                )
                # Backup SQLite aussi
                conn = get_db()
                c = conn.cursor()
                c.execute('INSERT OR REPLACE INTO memory (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)',
                          (key, value))
                conn.commit()
                conn.close()
                return f"✅ Mémorisé dans mémoire sémantique: {key} = {value[:100]}..."
            except Exception as e:
                return f"Erreur mémoire: {str(e)}"
        
        elif tool_name == "memory_recall":
            query = params.get("query", params.get("key", "all"))
            try:
                chroma_client = chromadb.HttpClient(host="chromadb", port=8000, settings=Settings(anonymized_telemetry=False))
                collection = chroma_client.get_or_create_collection(name="ai_orchestrator_memory")
                
                if query.lower() == "all":
                    # Récupérer toutes les mémoires
                    results = collection.get(limit=20, include=["documents", "metadatas"])
                    if results and results.get("documents"):
                        memories = []
                        for i, doc in enumerate(results["documents"]):
                            meta = results["metadatas"][i] if results.get("metadatas") else {}
                            mem_type = meta.get("type", "unknown")
                            memories.append(f"🧠 [{mem_type}] {doc}")
                        return "📚 Mémoires disponibles:\n" + "\n".join(memories)
                    return "Mémoire vide"
                else:
                    # Recherche sémantique
                    results = collection.query(query_texts=[query], n_results=5, include=["documents", "metadatas", "distances"])
                    if results and results.get("documents") and results["documents"][0]:
                        memories = []
                        for i, doc in enumerate(results["documents"][0]):
                            distance = results["distances"][0][i] if results.get("distances") else 0
                            # Convertir distance en score de similarité (plus petit = plus similaire)
                            similarity = max(0, 100 - (distance * 50))
                            memories.append(f"🧠 [{similarity:.1f}%] {doc}")
                        return f"🔍 Recherche '{query}':\n" + "\n".join(memories)
                    return f"Aucune mémoire trouvée pour: {query}"
            except Exception as e:
                # Fallback SQLite
                conn = get_db()
                c = conn.cursor()
                c.execute('SELECT key, value FROM memory ORDER BY updated_at DESC LIMIT 20')
                rows = c.fetchall()
                conn.close()
                if rows:
                    return "Mémoire (SQLite fallback):\n" + "\n".join([f"- {r[0]}: {r[1][:100]}" for r in rows])
                return f"Erreur ChromaDB: {str(e)}"
        
        elif tool_name == "web_request":
            url = params.get("url", "")
            method = params.get("method", "GET").upper()
            data = params.get("data", None)
            if not url:
                return "Erreur: URL requise"
            async with httpx.AsyncClient() as client:
                if method == "POST":
                    resp = await client.post(url, json=json.loads(data) if data else None, timeout=30)
                else:
                    resp = await client.get(url, timeout=30)
                return f"HTTP {resp.status_code}:\n{resp.text[:2000]}"
        
        elif tool_name == "memory_stats":
            if AUTO_LEARN_ENABLED:
                stats = get_memory_stats()
                result = f"📊 Statistiques mémoire:\n"
                result += f"   Total: {stats.get('total', 0)} souvenirs\n"
                result += f"   Par type: {stats.get('by_type', {})}\n"
                result += f"   Par catégorie: {stats.get('by_category', {})}"
                return result
            return "Auto-apprentissage non activé"
        
        elif tool_name == "final_answer":
            return params.get("answer", "")
        
        else:
            return f"Outil inconnu: {tool_name}"
    
    except subprocess.TimeoutExpired:
        return f"Timeout: l'outil {tool_name} a pris trop de temps"
    except Exception as e:
        return f"Erreur lors de l'exécution de {tool_name}: {str(e)}"

# ===== PARSING DES ACTIONS =====

def parse_action(text: str) -> tuple:
    """Parser une action du format: tool_name(param="value")"""
    text = text.strip()
    
    # CAS SPECIAL: final_answer
    if "final_answer" in text:
        # Support des triple quotes avec regex pour gérer les espaces
        # Ex: final_answer(answer = """...""")
        triple_match = re.search(r'answer\s*=\s*"""(.*?)"""', text, re.DOTALL)
        if triple_match:
            content = triple_match.group(1)
            content = content.replace('\\n', '\n')
            print(f"🎯 PARSE final_answer (triple quotes regex): {len(content)} chars")
            return "final_answer", {"answer": content.strip()}

        # Support des triple quotes méthode manuelle (fallback)
        if '"""' in text:
            start_marker = '"""'
            start_idx = text.find(start_marker)
            if start_idx != -1:
                # Chercher la fin
                end_idx = text.rfind(start_marker)
                if end_idx > start_idx:
                    content = text[start_idx + 3 : end_idx]
                    content = content.replace('\\n', '\n')
                    print(f"🎯 PARSE final_answer (triple quotes manual): {len(content)} chars")
                    return "final_answer", {"answer": content.strip()}

        # Méthode 1: Chercher answer="..." avec guillemets doubles
        match = re.search(r'final_answer\s*\(\s*answer\s*=\s*"(.*)"?\s*\)?$', text, re.DOTALL)
        if match:
            answer = match.group(1)
            # Nettoyage robuste de la fin
            answer = answer.rstrip()
            while answer and answer[-1] in '")\'\\':
                answer = answer[:-1]
            answer = answer.rstrip()
            # Remplacer les sauts de ligne échappés
            answer = answer.replace('\\n', '\n')
            print(f"🎯 PARSE final_answer (method1): {len(answer)} chars")
            return "final_answer", {"answer": answer}
        
        # Méthode 2: Chercher après answer=" jusqu'à la fin
        idx = text.find('answer="')
        if idx >= 0:
            content_start = idx + 8  # len('answer="')
            content = text[content_start:]
            
            # Nettoyage robuste de la fin (enlever les fermetures de fonction)
            # On cherche la dernière occurrence de ") qui ferme probablement la fonction
            last_quote_paren = content.rfind('")')
            if last_quote_paren != -1:
                content = content[:last_quote_paren]
            elif content.endswith('"'):
                content = content[:-1]
            
            # Si le contenu commence par "", c'était peut-être des triple quotes mal parsées
            if content.startswith('""'):
                content = content[2:]
            
            # Remplacer les sauts de ligne échappés par de vrais sauts de ligne
            content = content.replace('\\n', '\n')
            
            print(f"🎯 PARSE final_answer (method2): {len(content)} chars")
            return "final_answer", {"answer": content.strip()}
        
        # Méthode 3: guillemets simples
        idx = text.find("answer='")
        if idx >= 0:
            content_start = idx + 8
            content = text[content_start:]
            content = content.rstrip()
            if content.endswith("')"):
                content = content[:-2]
            elif content.endswith("'"):
                content = content[:-1]
            print(f"🎯 PARSE final_answer (method3): {len(content)} chars")
            # Nettoyage final - enlever ") ou ' ou " à la fin
            content = content.rstrip()
            if content.endswith('")'):
                content = content[:-2]
            elif content.endswith('"'):
                content = content[:-1]
            elif content.endswith("')"):
                content = content[:-2]
            elif content.endswith("'"):
                content = content[:-1]
            return "final_answer", {"answer": content.strip()}
    
    # Pattern standard pour les autres outils
    match = re.search(r'(\w+)\s*\(([^)]*)\)', text)
    if not match:
        return None, {}
    
    tool_name = match.group(1)
    params_str = match.group(2)
    
    params = {}
    if params_str.strip():
        for m in re.finditer(r'(\w+)\s*=\s*"([^"]*)"', params_str):
            params[m.group(1)] = m.group(2)
        for m in re.finditer(r"(\w+)\s*=\s*'([^']*)'", params_str):
            params[m.group(1)] = m.group(2)
    
    return tool_name, params

# ===== BOUCLE REACT =====

async def react_loop(
    user_message: str,
    model: str,
    conversation_id: str,
    uploaded_files: list = None,
    websocket: WebSocket = None
):
    """Boucle ReAct principale"""
    
    # Construire le contexte des fichiers uploadés
    files_context = ""
    if uploaded_files:
        files_context = "\n\nFichiers attachés par l'utilisateur:\n"
        for f in uploaded_files:
            files_context += f"- ID: {f['id']} | Nom: {f['filename']} | Type: {f['filetype']}\n"
        files_context += "\nUtilise analyze_file(file_id=\"...\") ou analyze_image(image_id=\"...\") pour les examiner.\n"
    
    # Prompt système
    tools_desc = "\n".join([
        f"- {name}: {info['description']}\n  Exemple: {info['example']}"
        for name, info in TOOLS.items()
    ])
    
    if PROMPTS_ENABLED:
        dynamic_ctx = ""
        if DYNAMIC_CONTEXT_ENABLED:
            dynamic_ctx = get_dynamic_context()
        system_prompt = build_system_prompt(tools_desc, files_context, dynamic_ctx)
    else:
        system_prompt = f"""Tu es un assistant IA expert pour l'infrastructure 4LB.ca.

Outils disponibles:
{tools_desc}
{files_context}

Utilise le format:
THINK: [Réflexion]
ACTION: tool(param="valeur")
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": user_message})
    
    iterations = 0
    full_response = ""
    
    while iterations < MAX_ITERATIONS:
        iterations += 1
        
        # Envoyer le statut via WebSocket
        if websocket:
            await websocket.send_json({
                "type": "thinking",
                "iteration": iterations,
                "message": f"Itération {iterations}/{MAX_ITERATIONS}..."
            })
        
        # Appeler le LLM
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{OLLAMA_URL}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 2000
                        }
                    },
                    timeout=180
                )
                data = response.json()
                assistant_text = data.get("message", {}).get("content", "")
        except Exception as e:
            error_msg = f"Erreur LLM: {str(e)}"
            if websocket:
                await websocket.send_json({"type": "error", "message": error_msg})
            return error_msg
        
        full_response += f"\n---\n**Itération {iterations}**\n{assistant_text}\n"
        
        # Envoyer la réponse partielle
        if websocket:
            await websocket.send_json({
                "type": "step",
                "iteration": iterations,
                "content": assistant_text
            })
        
        # Chercher une action
        lines = assistant_text.split('\n')
        action_line = None
        for line in lines:
            if line.strip().startswith('ACTION:'):
                action_line = line.replace('ACTION:', '').strip()
                break
            # Chercher directement un appel de fonction
            if re.match(r'^\w+\(.*\)\s*$', line.strip()):
                action_line = line.strip()
                break
        
        if not action_line:
            # Pas d'action trouvée, chercher dans tout le texte
            match = re.search(r'(\w+)\s*\([^)]+\)', assistant_text)
            if match:
                action_line = match.group(0)
        
        if action_line:
            tool_name, params = parse_action(action_line)
            
            if tool_name:
                # Vérifier si c'est final_answer
                if tool_name == "final_answer":
                    final = params.get("answer", assistant_text)
                    if websocket:
                        await websocket.send_json({
                            "type": "complete",
                            "answer": final,
                            "iterations": iterations,
                            "model": model
                        })
                    return final
                
                # Exécuter l'outil
                if websocket:
                    await websocket.send_json({
                        "type": "tool",
                        "tool": tool_name,
                        "params": params
                    })
                
                result = await execute_tool(tool_name, params, uploaded_files)
                
                # Ajouter au contexte avec urgence progressive
                messages.append({"role": "assistant", "content": assistant_text})
                
                if iterations >= 5:
                    msg = f"RÉSULTAT: {result[:500]}\n\n🚨 DERNIER TOUR! Réponds MAINTENANT: final_answer(answer=\"résumé de tes découvertes\")"
                elif iterations >= 4:
                    msg = f"RÉSULTAT: {result[:800]}\n\n⚠️ Plus que 2 tours! Conclus avec final_answer(answer=\"ta réponse\")"
                elif iterations >= 3:
                    msg = f"RÉSULTAT: {result}\n\n⚡ Tu as assez d'infos. Utilise final_answer(answer=\"ta réponse\") maintenant."
                else:
                    msg = f"RÉSULTAT: {result}\n\nContinue ou conclus avec final_answer(answer=\"ta réponse\")."
                messages.append({"role": "user", "content": msg})
                
                if websocket:
                    await websocket.send_json({
                        "type": "result",
                        "tool": tool_name,
                        "result": result[:1000]
                    })
            else:
                messages.append({"role": "assistant", "content": assistant_text})
                messages.append({"role": "user", "content": "Je n'ai pas compris l'action. Utilise le format exact: tool_name(param=\"valeur\")"})
        else:
            # Pas d'action, demander de continuer
            messages.append({"role": "assistant", "content": assistant_text})
            messages.append({"role": "user", "content": "Continue avec une ACTION ou utilise final_answer() pour conclure."})
    
    # Max iterations atteint - extraire une réponse utile
    # Chercher si le LLM a donné des infos dans son dernier message
    if "THINK:" in assistant_text:
        # Extraire juste la partie après THINK
        think_part = assistant_text.split("THINK:")[-1].split("ACTION:")[0].strip()
        timeout_msg = f"Voici ce que j'ai trouvé (analyse interrompue):\n{think_part[:500]}"
    else:
        timeout_msg = f"Analyse interrompue après {MAX_ITERATIONS} itérations. Derniers éléments analysés disponibles dans l'Activity Log."
    if websocket:
        await websocket.send_json({
            "type": "complete",
            "answer": timeout_msg,
            "iterations": iterations,
            "model": model
        })
    return timeout_msg

# ===== APPLICATION FASTAPI =====

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialisation au démarrage"""
    init_db()

    # Initialiser la base d'authentification
    if AUTH_ENABLED:
        try:
            init_auth_db()
            print("✅ Base d'authentification initialisée")
        except Exception as e:
            print(f"⚠️ Erreur init auth DB: {e}")

    # Démarrer la tâche de nettoyage du rate limiter
    if RATE_LIMIT_ENABLED:
        asyncio.create_task(cleanup_task())
        print("✅ Rate limiter démarré")

    yield

app = FastAPI(
    title="Orchestrateur IA 4LB.ca",
    description="Agent autonome avec boucle ReAct",
    version="2.0.0",
    lifespan=lifespan
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
        allow_headers=["*"]
    )

# Rate Limiting middleware
if RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)

# ===== MODÈLES PYDANTIC =====

class ChatRequest(BaseModel):
    message: str
    model: str = "auto"
    conversation_id: Optional[str] = None
    file_ids: Optional[List[str]] = None

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
            status_code=429,
            detail="Too many login attempts. Try again in 15 minutes."
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
    access_token = create_access_token(
        data={"sub": user.username, "scopes": user.scopes}
    )
    refresh_token = create_refresh_token(
        user_id=1,
        ip_address=ip,
        user_agent=request.headers.get("User-Agent", "")
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=3600
    )

@app.post("/api/auth/refresh")
async def refresh_token_endpoint(refresh_token: str):
    """Renouveler un token d'accès"""
    if not AUTH_ENABLED:
        raise HTTPException(status_code=501, detail="Authentication not enabled")

    user_id = verify_refresh_token(refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Récupérer l'utilisateur (simplifié - à améliorer avec l'ID réel)
    user = get_user("admin")
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token(
        data={"sub": user.username, "scopes": user.scopes}
    )

    return {"access_token": access_token, "token_type": "bearer", "expires_in": 3600}

@app.post("/api/auth/logout")
async def logout(refresh_token: str):
    """Révoquer un refresh token"""
    if not AUTH_ENABLED:
        raise HTTPException(status_code=501, detail="Authentication not enabled")

    revoke_refresh_token(refresh_token)
    return {"message": "Logged out successfully"}

@app.get("/api/auth/me")
async def get_me(current_user = Depends(get_current_active_user) if AUTH_ENABLED else None):
    """Obtenir les informations de l'utilisateur courant"""
    if not AUTH_ENABLED:
        return {"username": "anonymous", "scopes": ["admin"]}
    return current_user

@app.post("/api/auth/users")
async def create_new_user(
    user_data: UserCreate,
    current_user = Depends(get_current_admin_user) if AUTH_ENABLED else None
):
    """Créer un nouvel utilisateur (admin requis)"""
    if not AUTH_ENABLED:
        raise HTTPException(status_code=501, detail="Authentication not enabled")
    return create_user(user_data)

@app.post("/api/auth/apikeys")
async def create_new_api_key(
    name: str,
    scopes: List[str],
    expires_days: Optional[int] = None,
    current_user = Depends(get_current_admin_user) if AUTH_ENABLED else None
):
    """Créer une nouvelle API key (admin requis)"""
    if not AUTH_ENABLED:
        raise HTTPException(status_code=501, detail="Authentication not enabled")

    key = create_api_key(name, user_id=1, scopes=scopes, expires_days=expires_days)
    return {"key": key, "name": name, "scopes": scopes}

@app.get("/api/security/config")
async def get_security_config_endpoint(
    current_user = Depends(get_current_admin_user) if AUTH_ENABLED else None
):
    """Obtenir la configuration de sécurité (admin requis)"""
    if not SECURITY_ENABLED:
        return {"error": "Security module not enabled"}
    return get_security_config()

@app.get("/api/security/rate-limit-stats")
async def get_rate_limit_stats_endpoint(
    current_user = Depends(get_current_admin_user) if AUTH_ENABLED else None
):
    """Obtenir les statistiques de rate limiting (admin requis)"""
    if not RATE_LIMIT_ENABLED:
        return {"error": "Rate limiting not enabled"}
    return await get_rate_limit_stats()

@app.get("/api/models")
async def list_models():
    """Liste des modèles disponibles"""
    return {
        "models": [
            {"id": k, "name": v["name"], "description": v["description"]}
            for k, v in MODELS.items()
        ],
        "default": "auto"
    }

@app.get("/tools")
async def list_tools():
    """Liste des outils disponibles"""
    return {
        "tools": [
            {"name": name, "description": info["description"], "example": info["example"]}
            for name, info in TOOLS.items()
        ],
        "count": len(TOOLS)
    }


@app.get("/api/stats")
async def get_system_stats():
    """Get real-time system stats for dashboard"""
    import subprocess
    
    stats = {
        "cpu": {"percent": 0, "cores": 0},
        "memory": {"used_gb": 0, "total_gb": 0, "percent": 0},
        "gpu": {"name": "N/A", "memory_used": 0, "memory_total": 0, "percent": 0},
        "docker": {"running": 0, "total": 0}
    }
    
    try:
        # CPU usage
        cpu_result = subprocess.run(
            ["sh", "-c", "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'"],
            capture_output=True, text=True, timeout=5
        )
        stats["cpu"]["percent"] = round(float(cpu_result.stdout.strip() or 0), 1)
        
        cores_result = subprocess.run(["nproc"], capture_output=True, text=True, timeout=5)
        stats["cpu"]["cores"] = int(cores_result.stdout.strip() or 0)
        
        # Memory
        mem_result = subprocess.run(
            ["sh", "-c", "free -b | awk '/^Mem:/ {print $2, $3}'"],
            capture_output=True, text=True, timeout=5
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
            with open('/tmp/gpu-stats.txt', 'r') as f:
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
            capture_output=True, text=True, timeout=5
        )
        stats["docker"]["running"] = int(docker_result.stdout.strip() or 0)
        
        docker_all = subprocess.run(
            ["sh", "-c", "docker ps -aq 2>/dev/null | wc -l"],
            capture_output=True, text=True, timeout=5
        )
        stats["docker"]["total"] = int(docker_all.stdout.strip() or 0)
        
    except Exception as e:
        stats["error"] = str(e)
    
    return stats

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None)
):
    """Upload un fichier"""
    try:
        result = await save_upload(file, conversation_id)
        return {"success": True, "file": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(request: ChatRequest, current_user = Depends(get_current_active_user) if AUTH_ENABLED else None):
    """Endpoint chat synchrone"""
    # Déterminer le modèle
    has_image = False
    uploaded_files = []
    
    if request.file_ids:
        for fid in request.file_ids:
            info = get_upload_info(fid)
            if info:
                uploaded_files.append(info)
                if info['filetype'] == 'image':
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
        uploaded_files=uploaded_files
    )
    
    # Sauvegarder la réponse
    add_message(conv_id, "assistant", response, model)
    
    # Mettre à jour le titre si c'est le premier message
    messages = get_conversation_messages(conv_id)
    if len(messages) <= 2:
        title = request.message[:50] + "..." if len(request.message) > 50 else request.message
        update_conversation_title(conv_id, title)
    
    return {
        "response": response,
        "conversation_id": conv_id,
        "model_used": model
    }

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, token: str = Query(None)):
    """WebSocket pour chat en temps réel (authentification requise si AUTH_ENABLED)"""
    
    # Vérification du token si AUTH_ENABLED
    if AUTH_ENABLED:
        if not token:
            await websocket.close(code=4001, reason="Token required")
            return
        
        token_data = verify_token(token)
        if not token_data:
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
            
            # Traiter les fichiers
            has_image = False
            uploaded_files = []
            if file_ids:
                for fid in file_ids:
                    info = get_upload_info(fid)
                    if info:
                        uploaded_files.append(info)
                        if info['filetype'] == 'image':
                            has_image = True
            
            # Sélection du modèle
            if model_key == "auto":
                model = auto_select_model(message, has_image)
                await websocket.send_json({
                    "type": "model_selected",
                    "model": model,
                    "reason": "image attachée" if has_image else "analyse automatique"
                })
            else:
                model = MODELS.get(model_key, {}).get("model", DEFAULT_MODEL)
            
            # Créer conversation si nécessaire
            if not conv_id:
                conv_id = create_conversation()
                await websocket.send_json({
                    "type": "conversation_created",
                    "conversation_id": conv_id
                })
            
            # Sauvegarder message utilisateur
            add_message(conv_id, "user", message)
            
            # 🧠 AUTO-APPRENTISSAGE: Extraire et mémoriser les faits
            learned_facts = []
            if AUTO_LEARN_ENABLED:
                try:
                    learned_facts = auto_learn_from_message(message, conv_id)
                    if learned_facts:
                        await websocket.send_json({
                            "type": "activity",
                            "action": f"🧠 Auto-apprentissage: {len(learned_facts)} fait(s) mémorisé(s)",
                            "details": ", ".join(learned_facts)
                        })
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
                context_enhanced_message = f"[CONTEXTE MÉMOIRE]\n{context_str}\n[/CONTEXTE]\n\n{message}"
            
            response = await react_loop(
                user_message=context_enhanced_message,
                model=model,
                conversation_id=conv_id,
                uploaded_files=uploaded_files,
                websocket=websocket
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

# Servir le frontend
try:
    app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
except Exception as e:
    print(f"⚠️ Impossible de monter le frontend: {e}")

# ===== POINT D'ENTRÉE =====

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
