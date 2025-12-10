#!/usr/bin/env python3
"""
Orchestrateur IA 4LB.ca - Backend FastAPI v2.3 - RAG & Templates & Auto-correction
Agent autonome avec boucle ReAct, sélection auto de modèle, upload fichiers
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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ===== CONFIGURATION =====

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://10.10.10.46:11434")
DB_PATH = "/data/orchestrator.db"
UPLOAD_DIR = "/data/uploads"
MAX_ITERATIONS = 25

# Modèles disponibles avec leurs spécialités
MODELS = {
    "auto": {
        "name": "AUTO (Sélection automatique)",
        "description": "L'agent choisit le meilleur modèle selon la tâche",
        "model": None
    },
    "qwen-coder": {
        "name": "Qwen 2.5 Coder 32B",
        "description": "Code, scripts, debug, analyse technique",
        "model": "qwen2.5-coder:32b-instruct-q4_K_M",
        "keywords": ["code", "script", "python", "bash", "debug", "fonction", "variable", "api", "docker", "git", "npm", "programm"]
    },
    "deepseek-coder": {
        "name": "DeepSeek Coder 33B",
        "description": "Code alternatif, algorithmes complexes",
        "model": "deepseek-coder:33b",
        "keywords": ["algorithme", "optimis", "complex", "performance", "refactor"]
    },
    "llama-vision": {
        "name": "Llama 3.2 Vision 11B",
        "description": "Analyse d'images, OCR, vision",
        "model": "llama3.2-vision:11b-instruct-q8_0",
        "keywords": ["image", "photo", "screenshot", "capture", "voir", "regarde", "analyse visuel", "ocr"]
    },
    "qwen-vision": {
        "name": "Qwen3 VL 32B",
        "description": "Vision multimodale avancée",
        "model": "qwen3-vl:32b",
        "keywords": ["image", "multimodal", "vision", "graphique", "diagramme", "schéma"]
    }
}

DEFAULT_MODEL = "qwen2.5-coder:32b-instruct-q4_K_M"

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
    "memory_store": {
        "description": "Stocker une information en mémoire persistante",
        "parameters": {"key": "string - Clé", "value": "string - Valeur"},
        "example": "memory_store(key=\"projet\", value=\"Migration Docker\")"
    },
    "memory_recall": {
        "description": "Rappeler une information de la mémoire",
        "parameters": {"key": "string - Clé (ou 'all' pour tout)"},
        "example": "memory_recall(key=\"projet\")"
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
    "search_knowledge": {
        "description": "Rechercher dans la base de connaissances (documentation, projets indexés). Utilise la recherche sémantique via ChromaDB.",
        "parameters": {"query": "string - Ce que tu cherches", "collection": "string - Collection (défaut: documentation)", "n_results": "int - Nombre de résultats (défaut: 5)"},
        "example": "search_knowledge(query=\"configurer Traefik SSL\", collection=\"documentation\")"
    },
    "index_directory": {
        "description": "Indexer un répertoire dans ChromaDB pour permettre la recherche sémantique",
        "parameters": {"path": "string - Chemin du répertoire", "collection": "string - Nom de la collection", "extensions": "string - Extensions à indexer (défaut: .md,.txt,.py)"},
        "example": "index_directory(path=\"/home/lalpha/documentation\", collection=\"documentation\")"
    },
    "create_project": {
        "description": "Créer un nouveau projet complet avec structure, fichiers de base, et dépendances. Types: webapp, api, site, script",
        "parameters": {"type": "string - webapp|api|site|script", "name": "string - Nom du projet", "path": "string - Chemin parent (défaut: /home/lalpha/projets)", "framework": "string - react|nextjs|fastapi|flask (optionnel)"},
        "example": "create_project(type=\"api\", name=\"mon-api\", framework=\"fastapi\")"
    },
    "get_project_context": {
        "description": "Analyser un projet et récupérer son contexte (structure, README, package.json, requirements.txt)",
        "parameters": {"path": "string - Chemin du projet"},
        "example": "get_project_context(path=\"/home/lalpha/projets/ai-tools/ai-orchestrator\")"
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
    """Sélectionner automatiquement le meilleur modèle selon la tâche"""
    message_lower = message.lower()
    
    # Si une image est attachée, utiliser le modèle vision
    if has_image:
        return MODELS["llama-vision"]["model"]
    
    # Chercher des mots-clés pour chaque modèle
    scores = {}
    for model_key, model_info in MODELS.items():
        if model_key == "auto" or "keywords" not in model_info:
            continue
        score = 0
        for keyword in model_info.get("keywords", []):
            if keyword in message_lower:
                score += 1
        scores[model_key] = score
    
    # Choisir le modèle avec le meilleur score
    if scores:
        best_model = max(scores, key=scores.get)
        if scores[best_model] > 0:
            return MODELS[best_model]["model"]
    
    # Par défaut: qwen-coder (le plus polyvalent)
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
            if not path or not os.path.exists(path):
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
        
        elif tool_name == "memory_store":
            key = params.get("key", "")
            value = params.get("value", "")
            if not key:
                return "Erreur: clé requise"
            conn = get_db()
            c = conn.cursor()
            c.execute('INSERT OR REPLACE INTO memory (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)',
                      (key, value))
            conn.commit()
            conn.close()
            return f"Mémoire stockée: {key} = {value[:100]}..."
        
        elif tool_name == "memory_recall":
            key = params.get("key", "all")
            conn = get_db()
            c = conn.cursor()
            if key == "all":
                c.execute('SELECT key, value FROM memory ORDER BY updated_at DESC LIMIT 20')
                rows = c.fetchall()
                conn.close()
                if rows:
                    return "Mémoire:\n" + "\n".join([f"- {r[0]}: {r[1][:100]}" for r in rows])
                return "Mémoire vide"
            else:
                c.execute('SELECT value FROM memory WHERE key = ?', (key,))
                row = c.fetchone()
                conn.close()
                if row:
                    return f"Mémoire [{key}]: {row[0]}"
                return f"Clé non trouvée: {key}"
        
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
        
        elif tool_name == "create_plan":
            task = params.get("task", "")
            if not task:
                return "Erreur: description de la tâche requise"
            
            # Utiliser le LLM pour créer un plan
            plan_prompt = f"""Tu es un planificateur de tâches. Analyse cette demande et crée un plan d'exécution détaillé.

        TÂCHE: {task}

        RÈGLES:
        1. Décompose en étapes simples et séquentielles (max 8 étapes)
        2. Chaque étape doit être actionnable avec les outils disponibles
        3. Inclure des étapes de validation

        Réponds UNIQUEMENT avec un JSON valide de ce format:
        {{
            "task_summary": "résumé court de la tâche",
            "complexity": "simple|medium|complex",
            "estimated_steps": 5,
            "plan": [
        {{"step": 1, "action": "description", "tool": "tool_name", "validation": "comment vérifier"}},
        {{"step": 2, "action": "description", "tool": "tool_name", "validation": "comment vérifier"}}
            ]
        }}"""
            
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{OLLAMA_URL}/api/generate",
                        json={
                            "model": DEFAULT_MODEL,
                            "prompt": plan_prompt,
                            "stream": False,
                            "options": {"temperature": 0.3}
                        },
                        timeout=60
                    )
                    data = resp.json()
                    plan_text = data.get("response", "")
                    
                    # Extraire le JSON du plan
                    import re
                    json_match = re.search(r'\{.*\}', plan_text, re.DOTALL)
                    if json_match:
                        plan_json = json.loads(json_match.group())
                        # Stocker le plan en mémoire
                        conn = get_db()
                        c = conn.cursor()
                        c.execute('INSERT OR REPLACE INTO memory (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)',
                                  ("current_plan", json.dumps(plan_json)))
                        conn.commit()
                        conn.close()
                        
                        # Formater le plan pour l'affichage
                        result = f"📋 PLAN CRÉÉ: {plan_json.get('task_summary', task)}\n"
                        result += f"Complexité: {plan_json.get('complexity', 'medium')} | Étapes: {plan_json.get('estimated_steps', len(plan_json.get('plan', [])))}\n\n"
                        for step in plan_json.get("plan", []):
                            result += f"  {step['step']}. {step['action']}\n"
                            result += f"     → Outil: {step.get('tool', 'N/A')} | Validation: {step.get('validation', 'N/A')}\n"
                        return result
                    else:
                        return f"Plan généré (format libre):\n{plan_text}"
            except Exception as e:
                return f"Erreur création du plan: {str(e)}"
        
        elif tool_name == "validate_step":
            step_desc = params.get("step_description", "")
            expected = params.get("expected_result", "")
            
            if not step_desc:
                return "Erreur: description de l'étape requise"
            
            # Vérifications automatiques selon le type d'action
            validation_result = "✅ VALIDÉ"
            checks_performed = []
            
            # Si l'expected contient un chemin, vérifier l'existence
            path_match = re.search(r'(/[^\s]+)', expected)
            if path_match:
                path = path_match.group(1)
                if os.path.exists(path):
                    checks_performed.append(f"✓ Chemin existe: {path}")
                else:
                    validation_result = "❌ ÉCHEC"
                    checks_performed.append(f"✗ Chemin manquant: {path}")
            
            # Si l'expected mentionne un conteneur Docker
            if "docker" in expected.lower() or "conteneur" in expected.lower():
                container_match = re.search(r'(\w+-\w+|\w+)', expected)
                if container_match:
                    container = container_match.group(1)
                    result = subprocess.run(
                        f"docker ps --filter name={container} --format '{{{{.Status}}}}'",
                        shell=True, capture_output=True, text=True
                    )
                    if result.stdout.strip():
                        checks_performed.append(f"✓ Conteneur actif: {container}")
                    else:
                        validation_result = "⚠️ À VÉRIFIER"
                        checks_performed.append(f"? Conteneur non trouvé: {container}")
            
            return f"{validation_result}\nÉtape: {step_desc}\nAttendu: {expected}\n\nVérifications:\n" + "\n".join(checks_performed) if checks_performed else f"{validation_result}\nÉtape: {step_desc}\n(Validation manuelle requise)"
        

        elif tool_name == "search_knowledge":
            query = params.get("query", "")
            collection_name = params.get("collection", "documentation")
            n_results = int(params.get("n_results", 5))
            
            if not query:
                return "Erreur: query requise"
            
            try:
                # Utiliser l'API REST de ChromaDB
                chromadb_url = "http://chromadb:8000"
                
                async with httpx.AsyncClient() as client:
                    # Vérifier si la collection existe
                    collections_resp = await client.get(
                        f"{chromadb_url}/api/v2/tenants/default_tenant/databases/default_database/collections",
                        timeout=10
                    )
                    collections = collections_resp.json()
                    collection_exists = any(c.get("name") == collection_name for c in collections)
                    
                    if not collection_exists:
                        return f"Collection '{collection_name}' non trouvée. Collections disponibles: {[c.get('name') for c in collections]}\nUtilise index_directory() pour créer une collection."
                    
                    # Trouver l'ID de la collection
                    collection_id = None
                    for c in collections:
                        if c.get("name") == collection_name:
                            collection_id = c.get("id")
                            break
                    
                    # Rechercher avec query texte (ChromaDB génère les embeddings)
                    search_resp = await client.post(
                        f"{chromadb_url}/api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}/query",
                        json={
                            "query_texts": [query],
                            "n_results": n_results,
                            "include": ["documents", "metadatas", "distances"]
                        },
                        timeout=30
                    )
                    results = search_resp.json()
                    
                    if not results.get("documents") or not results["documents"][0]:
                        return f"Aucun résultat trouvé pour: {query}"
                    
                    # Formater les résultats
                    output = f"🔍 Recherche: '{query}' dans {collection_name}\n\n"
                    for i, (doc, meta, dist) in enumerate(zip(
                        results["documents"][0], 
                        results.get("metadatas", [[]])[0],
                        results.get("distances", [[]])[0]
                    )):
                        source = meta.get("source", "inconnu") if meta else "inconnu"
                        score = round(1 - dist, 3) if dist else "N/A"
                        output += f"--- Résultat {i+1} (score: {score}) ---\n"
                        output += f"Source: {source}\n"
                        output += f"{doc[:500]}...\n\n" if len(doc) > 500 else f"{doc}\n\n"
                    
                    return output
                    
            except Exception as e:
                return f"Erreur recherche ChromaDB: {str(e)}"
        
        elif tool_name == "index_directory":
            path = params.get("path", "")
            collection_name = params.get("collection", "")
            extensions = params.get("extensions", ".md,.txt,.py").split(",")
            
            if not path or not collection_name:
                return "Erreur: path et collection requis"
            
            if not os.path.exists(path):
                return f"Erreur: chemin non trouvé: {path}"
            
            try:
                chromadb_url = "http://chromadb:8000"
                
                # Collecter les fichiers
                files_content = []
                for root, dirs, files in os.walk(path):
                    # Ignorer certains dossiers
                    dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '__pycache__', 'venv', '.venv']]
                    for file in files:
                        if any(file.endswith(ext.strip()) for ext in extensions):
                            filepath = os.path.join(root, file)
                            try:
                                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                                    content = f.read()
                                    if content.strip():
                                        # Découper en chunks de ~1000 caractères
                                        chunks = [content[i:i+1000] for i in range(0, len(content), 800)]
                                        for j, chunk in enumerate(chunks):
                                            files_content.append({
                                                "id": f"{filepath}_{j}",
                                                "content": chunk,
                                                "source": filepath
                                            })
                            except Exception as e:
                                pass
                
                if not files_content:
                    return f"Aucun fichier trouvé avec les extensions: {extensions}"
                
                async with httpx.AsyncClient() as client:
                    # Créer ou récupérer la collection
                    create_resp = await client.post(
                        f"{chromadb_url}/api/v2/tenants/default_tenant/databases/default_database/collections",
                        json={
                            "name": collection_name,
                            "metadata": {"indexed_path": path}
                        },
                        timeout=10
                    )
                    
                    # Récupérer l'ID de la collection
                    collections_resp = await client.get(
                        f"{chromadb_url}/api/v2/tenants/default_tenant/databases/default_database/collections",
                        timeout=10
                    )
                    collections = collections_resp.json()
                    collection_id = None
                    for c in collections:
                        if c.get("name") == collection_name:
                            collection_id = c.get("id")
                            break
                    
                    if not collection_id:
                        return "Erreur: impossible de créer la collection"
                    
                    # Ajouter les documents par batch
                    batch_size = 50
                    total_added = 0
                    
                    for i in range(0, len(files_content), batch_size):
                        batch = files_content[i:i+batch_size]
                        add_resp = await client.post(
                            f"{chromadb_url}/api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}/add",
                            json={
                                "ids": [item["id"] for item in batch],
                                "documents": [item["content"] for item in batch],
                                "metadatas": [{"source": item["source"]} for item in batch]
                            },
                            timeout=60
                        )
                        total_added += len(batch)
                    
                    return f"✅ Indexation terminée!\nCollection: {collection_name}\nDocuments indexés: {total_added}\nChemin: {path}\nExtensions: {extensions}"
                    
            except Exception as e:
                return f"Erreur indexation: {str(e)}"
        
        elif tool_name == "get_project_context":
            path = params.get("path", "")
            if not path or not os.path.exists(path):
                return f"Erreur: chemin non trouvé: {path}"
            
            context = f"📁 Contexte du projet: {path}\n\n"
            
            # Structure du projet
            result = subprocess.run(
                f"find {path} -maxdepth 3 -type f | head -50",
                shell=True, capture_output=True, text=True, timeout=10
            )
            context += f"=== Structure (50 premiers fichiers) ===\n{result.stdout}\n\n"
            
            # README
            readme_paths = ["README.md", "README.txt", "readme.md"]
            for readme in readme_paths:
                readme_path = os.path.join(path, readme)
                if os.path.exists(readme_path):
                    with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()[:2000]
                    context += f"=== {readme} ===\n{content}\n\n"
                    break
            
            # package.json / requirements.txt
            pkg_files = ["package.json", "requirements.txt", "pyproject.toml", "Cargo.toml"]
            for pkg in pkg_files:
                pkg_path = os.path.join(path, pkg)
                if os.path.exists(pkg_path):
                    with open(pkg_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()[:1500]
                    context += f"=== {pkg} ===\n{content}\n\n"
            
            # docker-compose.yml
            docker_path = os.path.join(path, "docker-compose.yml")
            if os.path.exists(docker_path):
                with open(docker_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()[:1500]
                context += f"=== docker-compose.yml ===\n{content}\n\n"
            
            return context
        
        elif tool_name == "create_project":
            project_type = params.get("type", "")
            name = params.get("name", "")
            base_path = params.get("path", "/home/lalpha/projets")
            framework = params.get("framework", "")
            
            if not project_type or not name:
                return "Erreur: type et name requis"
            
            if project_type not in ["webapp", "api", "site", "script"]:
                return f"Erreur: type invalide. Valeurs: webapp, api, site, script"
            
            project_path = os.path.join(base_path, name)
            
            if os.path.exists(project_path):
                return f"Erreur: le projet existe déjà: {project_path}"
            
            try:
                os.makedirs(project_path, exist_ok=True)
                created_files = []
                
                # ===== TEMPLATES PAR TYPE =====
                
                if project_type == "api":
                    # Structure API FastAPI
                    os.makedirs(f"{project_path}/app", exist_ok=True)
                    os.makedirs(f"{project_path}/tests", exist_ok=True)
                    
                    # main.py
                    main_content = '''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="{name}", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {{"message": "Bienvenue sur {name}!"}}

@app.get("/health")
def health():
    return {{"status": "healthy"}}
'''.format(name=name)
                    with open(f"{project_path}/app/main.py", 'w') as f:
                        f.write(main_content)
                    created_files.append("app/main.py")
                    
                    # __init__.py
                    with open(f"{project_path}/app/__init__.py", 'w') as f:
                        f.write("")
                    created_files.append("app/__init__.py")
                    
                    # requirements.txt
                    req_content = '''fastapi==0.115.0
uvicorn[standard]==0.32.0
httpx==0.27.2
pydantic==2.9.2
python-dotenv==1.0.0
'''
                    with open(f"{project_path}/requirements.txt", 'w') as f:
                        f.write(req_content)
                    created_files.append("requirements.txt")
                    
                    # Dockerfile
                    dockerfile = '''FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''
                    with open(f"{project_path}/Dockerfile", 'w') as f:
                        f.write(dockerfile)
                    created_files.append("Dockerfile")
                    
                    # docker-compose.yml
                    compose = f'''services:
  {name}:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    environment:
      - ENV=development
'''
                    with open(f"{project_path}/docker-compose.yml", 'w') as f:
                        f.write(compose)
                    created_files.append("docker-compose.yml")
                
                elif project_type == "webapp":
                    # Structure React/Vite
                    os.makedirs(f"{project_path}/src", exist_ok=True)
                    os.makedirs(f"{project_path}/public", exist_ok=True)
                    
                    # package.json
                    pkg = f'''{{
  "name": "{name}",
  "version": "1.0.0",
  "type": "module",
  "scripts": {{
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  }},
  "dependencies": {{
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  }},
  "devDependencies": {{
    "@vitejs/plugin-react": "^4.3.0",
    "vite": "^5.4.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }}
}}
'''
                    with open(f"{project_path}/package.json", 'w') as f:
                        f.write(pkg)
                    created_files.append("package.json")
                    
                    # vite.config.js
                    vite_config = '''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 3000 }
})
'''
                    with open(f"{project_path}/vite.config.js", 'w') as f:
                        f.write(vite_config)
                    created_files.append("vite.config.js")
                    
                    # index.html
                    html = f'''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name}</title>
</head>
<body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
</body>
</html>
'''
                    with open(f"{project_path}/index.html", 'w') as f:
                        f.write(html)
                    created_files.append("index.html")
                    
                    # src/main.jsx
                    main_jsx = '''import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
'''
                    with open(f"{project_path}/src/main.jsx", 'w') as f:
                        f.write(main_jsx)
                    created_files.append("src/main.jsx")
                    
                    # src/App.jsx
                    app_jsx = f'''export default function App() {{
  return (
    <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">🚀 {name}</h1>
        <p className="text-gray-400">Votre application est prête!</p>
      </div>
    </div>
  )
}}
'''
                    with open(f"{project_path}/src/App.jsx", 'w') as f:
                        f.write(app_jsx)
                    created_files.append("src/App.jsx")
                    
                    # src/index.css
                    css = '''@tailwind base;
@tailwind components;
@tailwind utilities;
'''
                    with open(f"{project_path}/src/index.css", 'w') as f:
                        f.write(css)
                    created_files.append("src/index.css")
                
                elif project_type == "site":
                    # Site statique HTML/CSS/JS
                    os.makedirs(f"{project_path}/css", exist_ok=True)
                    os.makedirs(f"{project_path}/js", exist_ok=True)
                    os.makedirs(f"{project_path}/images", exist_ok=True)
                    
                    # index.html
                    html = f'''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name}</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <header>
        <nav>
            <h1>{name}</h1>
        </nav>
    </header>
    
    <main>
        <section class="hero">
            <h2>Bienvenue sur {name}</h2>
            <p>Votre site est prêt!</p>
        </section>
    </main>
    
    <footer>
        <p>&copy; 2025 {name}</p>
    </footer>
    
    <script src="js/main.js"></script>
</body>
</html>
'''
                    with open(f"{project_path}/index.html", 'w') as f:
                        f.write(html)
                    created_files.append("index.html")
                    
                    # css/style.css
                    css = '''* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: system-ui, sans-serif; line-height: 1.6; }
header { background: #1a1a2e; color: white; padding: 1rem 2rem; }
main { min-height: 80vh; padding: 2rem; }
.hero { text-align: center; padding: 4rem 2rem; }
footer { background: #1a1a2e; color: white; text-align: center; padding: 1rem; }
'''
                    with open(f"{project_path}/css/style.css", 'w') as f:
                        f.write(css)
                    created_files.append("css/style.css")
                    
                    # js/main.js
                    js = '''console.log("Site chargé!");
'''
                    with open(f"{project_path}/js/main.js", 'w') as f:
                        f.write(js)
                    created_files.append("js/main.js")
                
                elif project_type == "script":
                    # Script Python
                    os.makedirs(f"{project_path}/src", exist_ok=True)
                    os.makedirs(f"{project_path}/tests", exist_ok=True)
                    
                    # main.py
                    main_py = f'''#!/usr/bin/env python3
"""
{name} - Script principal
"""

import argparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="{name}")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbose")
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Démarrage de {name}...")
    # TODO: Ajouter la logique ici
    logger.info("Terminé!")

if __name__ == "__main__":
    main()
'''
                    with open(f"{project_path}/src/main.py", 'w') as f:
                        f.write(main_py)
                    os.chmod(f"{project_path}/src/main.py", 0o755)
                    created_files.append("src/main.py")
                    
                    # requirements.txt
                    with open(f"{project_path}/requirements.txt", 'w') as f:
                        f.write("# Dépendances\n")
                    created_files.append("requirements.txt")
                
                # ===== FICHIERS COMMUNS =====
                
                # README.md
                readme = f'''# {name}

> Projet créé par AI Orchestrator

## Description

{project_type.upper()} project.

## Installation

```bash
cd {project_path}
{"npm install" if project_type == "webapp" else "pip install -r requirements.txt" if project_type in ["api", "script"] else "# Ouvrir index.html"}
```

## Utilisation

```bash
{"npm run dev" if project_type == "webapp" else "uvicorn app.main:app --reload" if project_type == "api" else "python src/main.py" if project_type == "script" else "# Ouvrir dans un navigateur"}
```

---
*Créé le {__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")}*
'''
                with open(f"{project_path}/README.md", 'w') as f:
                    f.write(readme)
                created_files.append("README.md")
                
                # .gitignore
                gitignore = '''# Dependencies
node_modules/
venv/
.venv/
__pycache__/
*.pyc

# Build
dist/
build/
*.egg-info/

# Environment
.env
.env.local

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
'''
                with open(f"{project_path}/.gitignore", 'w') as f:
                    f.write(gitignore)
                created_files.append(".gitignore")
                
                # Initialiser git
                subprocess.run(f"cd {project_path} && git init", shell=True, capture_output=True)
                
                return f"""✅ Projet créé avec succès!

📁 Chemin: {project_path}
📦 Type: {project_type}
🔧 Framework: {framework or "aucun"}

Fichiers créés:
{chr(10).join(f"  - {f}" for f in created_files)}

Prochaines étapes:
```bash
cd {project_path}
{"npm install && npm run dev" if project_type == "webapp" else "pip install -r requirements.txt && uvicorn app.main:app --reload" if project_type == "api" else "python src/main.py --help" if project_type == "script" else "# Ouvrir index.html dans un navigateur"}
```
"""
                
            except Exception as e:
                return f"Erreur création projet: {str(e)}"
        

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
    """Parser une action du format: tool_name(param="value", param2="value2")"""
    # Pattern pour capturer tool_name(...)
    pattern = r'(\w+)\s*\((.*?)\)\s*$'
    match = re.search(pattern, text.strip(), re.DOTALL)
    
    if not match:
        return None, {}
    
    tool_name = match.group(1)
    params_str = match.group(2)
    
    # Parser les paramètres
    params = {}
    if params_str.strip():
        # Pattern pour key="value" ou key='value'
        param_pattern = r'(\w+)\s*=\s*["\'](.+?)["\']'
        for m in re.finditer(param_pattern, params_str, re.DOTALL):
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
    
    system_prompt = f"""Tu es un agent IA autonome pour l'infrastructure de 4LB.ca.
Tu as accès au serveur Ubuntu (10.10.10.46), Docker, UDM-Pro UniFi, et Ollama.

## STRUCTURE DES PROJETS

### Projets Clients
- **JSR DEV**: /home/lalpha/projets/clients/jsr/JSR/ → https://jsr.4lb.ca
- **JSR PROD**: /home/lalpha/projets/clients/jsr/JSR-solutions/ → https://jsr-solutions.ca

### Projets AI
- **AI Orchestrator**: /home/lalpha/projets/ai-tools/ai-orchestrator/
- **MCP Servers**: /home/lalpha/projets/ai-tools/mcp-servers/

### Infrastructure
- **Unified Stack**: /home/lalpha/projets/infrastructure/unified-stack/
- Gestion: ./stack.sh (up, down, status, restart, logs, test)

## MÉTHODOLOGIE REACT

Tu dois suivre strictement ce cycle:
1. **THINK**: Réfléchis à ce que tu dois faire
2. **ACTION**: Exécute UNE SEULE action avec la syntaxe exacte
3. **OBSERVE**: Analyse le résultat
4. **REPEAT**: Continue jusqu'à avoir la réponse finale

## OUTILS DISPONIBLES

{tools_desc}

## RÈGLES STRICTES

1. **UNE SEULE ACTION PAR RÉPONSE** - Jamais plusieurs outils à la fois
2. **SYNTAXE EXACTE**: tool_name(param="valeur") - Les guillemets sont obligatoires
3. **FINAL_ANSWER OBLIGATOIRE**: Termine TOUJOURS par final_answer(answer="...")
4. **Maximum {MAX_ITERATIONS} itérations**
5. **JAMAIS SUDO** - Tu tournes en root, sudo n'existe pas dans le conteneur

## STRATÉGIE DE PLANIFICATION

Pour les tâches COMPLEXES (création de projet, multiple fichiers, configuration):
1. **COMMENCE PAR** create_plan(task="...") pour décomposer la tâche
2. **SUIS LE PLAN** étape par étape
3. **VALIDE CHAQUE ÉTAPE** avec validate_step() si nécessaire

## AUTO-CORRECTION

Si une erreur survient:
1. **ANALYSE** le message d'erreur
2. **ADAPTE** ta commande (permissions, chemin, syntaxe)
3. **RETENTE** jusqu'à 3 fois avant d'abandonner
{files_context}
## FORMAT DE RÉPONSE

THINK: [ta réflexion]

ACTION: tool_name(param="valeur")

Puis attends le résultat avant de continuer."""

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
                
                # === AUTO-CORRECTION : Détecter les erreurs et aider le LLM ===
                error_patterns = ["Erreur:", "error:", "Error:", "failed", "Failed", "FAILED", 
                                  "Permission denied", "not found", "No such file", "timeout", "Timeout"]
                is_error = any(pattern in result for pattern in error_patterns)
                
                correction_hint = ""
                if is_error:
                    # Analyser le type d'erreur et suggérer une correction
                    if "Permission denied" in result:
                        correction_hint = "\n\n⚠️ ERREUR DE PERMISSION: Essaie avec sudo ou vérifie les droits du fichier."
                    elif "not found" in result.lower() or "No such file" in result:
                        correction_hint = "\n\n⚠️ FICHIER/DOSSIER NON TROUVÉ: Vérifie le chemin ou crée le dossier parent avec mkdir -p."
                    elif "timeout" in result.lower():
                        correction_hint = "\n\n⚠️ TIMEOUT: La commande a pris trop de temps. Essaie une commande plus simple."
                    elif "connection" in result.lower():
                        correction_hint = "\n\n⚠️ ERREUR CONNEXION: Vérifie que le service est démarré et accessible."
                    else:
                        correction_hint = "\n\n⚠️ ERREUR DÉTECTÉE: Analyse l'erreur et adapte ta commande. Tu peux retenter jusqu'à 3 fois."
                
                # Ajouter au contexte
                messages.append({"role": "assistant", "content": assistant_text})
                observation_msg = f"OBSERVATION:\n{result}{correction_hint}\n\nContinue ton analyse ou utilise final_answer() si tu as terminé."
                messages.append({"role": "user", "content": observation_msg})
                
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
    
    # Max iterations atteint
    timeout_msg = f"Maximum d'itérations atteint ({MAX_ITERATIONS}). Dernière réponse:\n{assistant_text}"
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
    yield

app = FastAPI(
    title="Orchestrateur IA 4LB.ca",
    description="Agent autonome avec boucle ReAct",
    version="2.3.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# ===== MODÈLES PYDANTIC =====

class ChatRequest(BaseModel):
    message: str
    model: str = "auto"
    conversation_id: Optional[str] = None
    file_ids: Optional[List[str]] = None

class ConversationUpdate(BaseModel):
    title: str

# ===== ENDPOINTS API =====

@app.get("/")
async def root():
    return {"status": "ok", "service": "AI Orchestrator v2.0", "tools": len(TOOLS)}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "2.3.0",
        "tools_count": len(TOOLS),
        "models_count": len(MODELS),
        "ollama_url": OLLAMA_URL
    }

@app.get("/models")
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
async def chat(request: ChatRequest):
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
async def websocket_chat(websocket: WebSocket):
    """WebSocket pour chat en temps réel"""
    await websocket.accept()
    
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
            
            # Exécuter la boucle ReAct
            response = await react_loop(
                user_message=message,
                model=model,
                conversation_id=conv_id,
                uploaded_files=uploaded_files,
                websocket=websocket
            )
            
            # Sauvegarder la réponse
            add_message(conv_id, "assistant", response, model)
            
    except WebSocketDisconnect:
        pass
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

# ===== POINT D'ENTRÉE =====

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
