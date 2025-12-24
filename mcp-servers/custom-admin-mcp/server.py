#!/usr/bin/env python3
"""
MCP Server 4LB.ca v2.2 - Double interface: MCP SSE + REST API
Pour Gemini (MCP) ET pour l'Orchestrateur (REST)
"""

from mcp.server.fastmcp import FastMCP
import subprocess
import os
import shutil
from datetime import datetime
from pathlib import Path
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import threading
import asyncio

# ============================================================
# CONFIGURATION
# ============================================================

HOST = "0.0.0.0"
MCP_PORT = 8888   # Pour Gemini (MCP SSE)
REST_PORT = 8889  # Pour l'Orchestrateur (REST API)

ALLOWED_PATHS = [
    "/home/lalpha",
    "/home/lalpha/projets",
    "/home/lalpha/scripts",
    "/home/lalpha/documentation",
    "/tmp"
]

FORBIDDEN_PATHS = [".env", "id_rsa", "id_ed25519", ".ssh/", "secrets", ".git/objects"]
FORBIDDEN_EXTENSIONS = [".key", ".pem", ".p12"]

def is_path_allowed(path: str, write: bool = False) -> tuple:
    try:
        abs_path = os.path.abspath(os.path.expanduser(path))
        for forbidden in FORBIDDEN_PATHS:
            if forbidden in abs_path:
                return False, f"Chemin interdit: contient '{forbidden}'"
        if write:
            for ext in FORBIDDEN_EXTENSIONS:
                if abs_path.endswith(ext):
                    return False, f"Extension interdite: '{ext}'"
        for allowed in ALLOWED_PATHS:
            if abs_path.startswith(allowed):
                return True, "OK"
        return False, f"Chemin hors zone autorisée"
    except Exception as e:
        return False, f"Erreur: {str(e)}"

# ============================================================
# FONCTIONS OUTILS (partagées)
# ============================================================

def _get_gpu_status() -> str:
    try:
        result = subprocess.check_output([
            "nvidia-smi", 
            "--query-gpu=name,utilization.gpu,memory.total,memory.used,memory.free,temperature.gpu,power.draw",
            "--format=csv,noheader"
        ])
        data = result.decode().strip().split(", ")
        return f"🎮 GPU: {data[0]} | {data[1]}% | VRAM: {data[3]}/{data[2]} | {data[5]}°C | {data[6]}W"
    except Exception as e:
        return f"❌ Erreur GPU: {str(e)}"

def _get_system_status() -> str:
    try:
        cpu = subprocess.check_output(["nproc"]).decode().strip()
        load = subprocess.check_output(["cat", "/proc/loadavg"]).decode().strip()
        mem = subprocess.check_output(["free", "-h", "--si"]).decode()
        disk = subprocess.check_output(["df", "-h", "/"]).decode()
        return f"🖥️ CPU: {cpu} cores | Load: {load}\n📊 Mémoire:\n{mem}\n💾 Disque:\n{disk}"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

def _get_docker_status() -> str:
    try:
        result = subprocess.check_output(["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"])
        return f"🐳 Docker:\n{result.decode()}"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

def _read_file(path: str, lines: int = 0) -> str:
    allowed, msg = is_path_allowed(path, write=False)
    if not allowed:
        return f"❌ {msg}"
    try:
        abs_path = os.path.abspath(os.path.expanduser(path))
        if not os.path.exists(abs_path):
            return f"❌ Fichier non trouvé: {abs_path}"
        with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
            if lines > 0:
                content = ''.join(f.readlines()[:lines])
            else:
                content = f.read()
        return f"📄 {abs_path} ({os.path.getsize(abs_path)} bytes):\n\n{content}"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

def _write_file(path: str, content: str, backup: bool = True) -> str:
    allowed, msg = is_path_allowed(path, write=True)
    if not allowed:
        return f"❌ {msg}"
    try:
        abs_path = os.path.abspath(os.path.expanduser(path))
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        if backup and os.path.exists(abs_path):
            backup_path = f"{abs_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(abs_path, backup_path)
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"✅ Fichier écrit: {abs_path} ({len(content)} chars)"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

def _patch_file(path: str, old_text: str, new_text: str, backup: bool = True) -> str:
    allowed, msg = is_path_allowed(path, write=True)
    if not allowed:
        return f"❌ {msg}"
    try:
        abs_path = os.path.abspath(os.path.expanduser(path))
        if not os.path.exists(abs_path):
            return f"❌ Fichier non trouvé: {abs_path}"
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if old_text not in content:
            return f"❌ Texte non trouvé dans {abs_path}"
        count = content.count(old_text)
        if backup:
            backup_path = f"{abs_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(abs_path, backup_path)
        new_content = content.replace(old_text, new_text)
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return f"✅ Patch: {count} occurrence(s) dans {abs_path}"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

def _list_directory(path: str) -> str:
    allowed, msg = is_path_allowed(path, write=False)
    if not allowed:
        return f"❌ {msg}"
    try:
        abs_path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(abs_path):
            return f"❌ N'est pas un répertoire: {abs_path}"
        items = sorted(os.listdir(abs_path))
        result = []
        for item in items:
            full_path = os.path.join(abs_path, item)
            if os.path.isdir(full_path):
                result.append(f"📁 {item}/")
            else:
                size = os.path.getsize(full_path)
                result.append(f"📄 {item} ({size} bytes)")
        return f"📂 {abs_path}:\n" + '\n'.join(result)
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

def _run_command(command: str, cwd: str = "/home/lalpha") -> str:
    allowed, msg = is_path_allowed(cwd, write=False)
    if not allowed:
        return f"❌ {msg}"
    forbidden = ["rm -rf /", "mkfs", "dd if=", "> /dev/", "chmod 777 /"]
    for f in forbidden:
        if f in command:
            return f"❌ Commande interdite: {f}"
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        if len(output) > 10000:
            output = output[:10000] + "\n... (tronqué)"
        status = "✅" if result.returncode == 0 else "❌"
        return f"{status} Code {result.returncode}:\n{output}"
    except subprocess.TimeoutExpired:
        return "❌ Timeout (>60s)"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

def _docker_logs(container: str, lines: int = 50) -> str:
    try:
        result = subprocess.check_output(["docker", "logs", "--tail", str(lines), container], stderr=subprocess.STDOUT)
        return f"📋 Logs {container}:\n{result.decode()}"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

def _docker_restart(container: str) -> str:
    try:
        subprocess.check_output(["docker", "restart", container])
        return f"✅ Container {container} redémarré"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

def _git_status(repo_path: str) -> str:
    allowed, msg = is_path_allowed(repo_path, write=False)
    if not allowed:
        return f"❌ {msg}"
    try:
        result = subprocess.check_output(["git", "status", "--short"], cwd=repo_path, stderr=subprocess.STDOUT)
        return f"📊 Git status:\n{result.decode()}"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

def _git_commit(repo_path: str, message: str, add_all: bool = True) -> str:
    allowed, msg = is_path_allowed(repo_path, write=True)
    if not allowed:
        return f"❌ {msg}"
    try:
        if add_all:
            subprocess.check_output(["git", "add", "-A"], cwd=repo_path)
        result = subprocess.check_output(["git", "commit", "-m", message], cwd=repo_path, stderr=subprocess.STDOUT)
        return f"✅ Commit:\n{result.decode()}"
    except subprocess.CalledProcessError as e:
        return f"❌ Erreur: {e.output.decode()}"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

def _python_check_syntax(path: str) -> str:
    allowed, msg = is_path_allowed(path, write=False)
    if not allowed:
        return f"❌ {msg}"
    try:
        result = subprocess.run(["python3", "-m", "py_compile", path], capture_output=True, text=True)
        if result.returncode == 0:
            return f"✅ Syntaxe OK: {path}"
        return f"❌ Erreur:\n{result.stderr}"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

# ============================================================
# MCP SERVER (Port 8888 pour Gemini)
# ============================================================

mcp = FastMCP("4LB-Admin-Server-v2", host=HOST, port=MCP_PORT)

@mcp.tool()
def get_gpu_status() -> str:
    """Récupère l'état du GPU NVIDIA."""
    return _get_gpu_status()

@mcp.tool()
def get_system_status() -> str:
    """État système (CPU, RAM, Disk, Load)."""
    return _get_system_status()

@mcp.tool()
def get_docker_status() -> str:
    """Liste les containers Docker."""
    return _get_docker_status()

@mcp.tool()
def read_file(path: str, lines: int = 0) -> str:
    """Lire un fichier."""
    return _read_file(path, lines)

@mcp.tool()
def write_file(path: str, content: str, backup: bool = True) -> str:
    """Écrire un fichier avec backup."""
    return _write_file(path, content, backup)

@mcp.tool()
def patch_file(path: str, old_text: str, new_text: str, backup: bool = True) -> str:
    """Modifier du texte (search/replace)."""
    return _patch_file(path, old_text, new_text, backup)

@mcp.tool()
def list_directory(path: str) -> str:
    """Lister un répertoire."""
    return _list_directory(path)

@mcp.tool()
def run_command(command: str, cwd: str = "/home/lalpha") -> str:
    """Exécuter une commande shell."""
    return _run_command(command, cwd)

@mcp.tool()
def docker_logs(container: str, lines: int = 50) -> str:
    """Voir les logs d'un container."""
    return _docker_logs(container, lines)

@mcp.tool()
def docker_restart(container: str) -> str:
    """Redémarrer un container."""
    return _docker_restart(container)

@mcp.tool()
def git_status(repo_path: str = "/home/lalpha/projets") -> str:
    """Statut Git."""
    return _git_status(repo_path)

@mcp.tool()
def git_commit(repo_path: str, message: str, add_all: bool = True) -> str:
    """Créer un commit Git."""
    return _git_commit(repo_path, message, add_all)

@mcp.tool()
def python_check_syntax(path: str) -> str:
    """Vérifier syntaxe Python."""
    return _python_check_syntax(path)

# ============================================================
# REST API SERVER (Port 8889 pour l'Orchestrateur)
# ============================================================

rest_app = FastAPI(title="4LB MCP REST API", version="2.2")

rest_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modèles Pydantic
class CommandRequest(BaseModel):
    command: str
    cwd: str = "/home/lalpha"

class FileReadRequest(BaseModel):
    path: str
    lines: int = 0

class FileWriteRequest(BaseModel):
    path: str
    content: str
    backup: bool = True

class FilePatchRequest(BaseModel):
    path: str
    old_text: str
    new_text: str
    backup: bool = True

class DockerRequest(BaseModel):
    container: str
    lines: int = 50

class GitCommitRequest(BaseModel):
    repo_path: str
    message: str
    add_all: bool = True

# Endpoints REST
@rest_app.get("/")
def root():
    return {"server": "4LB MCP REST API v2.2", "status": "running"}

@rest_app.get("/health")
def health():
    return {"status": "ok"}

@rest_app.post("/tools/run_command")
def api_run_command(req: CommandRequest):
    return {"result": _run_command(req.command, req.cwd)}

@rest_app.post("/tools/read_file")
def api_read_file(req: FileReadRequest):
    return {"result": _read_file(req.path, req.lines)}

@rest_app.post("/tools/write_file")
def api_write_file(req: FileWriteRequest):
    return {"result": _write_file(req.path, req.content, req.backup)}

@rest_app.post("/tools/patch_file")
def api_patch_file(req: FilePatchRequest):
    return {"result": _patch_file(req.path, req.old_text, req.new_text, req.backup)}

@rest_app.post("/tools/list_directory")
def api_list_directory(path: str = "/home/lalpha"):
    return {"result": _list_directory(path)}

@rest_app.get("/tools/get_gpu_status")
def api_gpu():
    return {"result": _get_gpu_status()}

@rest_app.get("/tools/get_system_status")
def api_system():
    return {"result": _get_system_status()}

@rest_app.get("/tools/get_docker_status")
def api_docker():
    return {"result": _get_docker_status()}

@rest_app.post("/tools/docker_logs")
def api_docker_logs(req: DockerRequest):
    return {"result": _docker_logs(req.container, req.lines)}

@rest_app.post("/tools/docker_restart")
def api_docker_restart(container: str):
    return {"result": _docker_restart(container)}

@rest_app.get("/tools/git_status")
def api_git_status(repo: str = "/home/lalpha/projets"):
    return {"result": _git_status(repo)}

@rest_app.post("/tools/git_commit")
def api_git_commit(req: GitCommitRequest):
    return {"result": _git_commit(req.repo_path, req.message, req.add_all)}

@rest_app.post("/tools/python_check_syntax")
def api_python_check(path: str):
    return {"result": _python_check_syntax(path)}

# ============================================================
# LANCEMENT DUAL (MCP + REST)
# ============================================================

def run_rest_server():
    """Lance le serveur REST en thread séparé"""
    uvicorn.run(rest_app, host=HOST, port=REST_PORT, log_level="warning")

if __name__ == "__main__":
    print("🚀 MCP Server 4LB v2.2 - Double interface")
    print(f"📡 MCP SSE (Gemini): http://{HOST}:{MCP_PORT}/sse")
    print(f"🌐 REST API (Orchestrateur): http://{HOST}:{REST_PORT}/tools/*")
    print(f"📁 Chemins autorisés: {ALLOWED_PATHS}")
    
    # Lancer REST API en thread séparé
    rest_thread = threading.Thread(target=run_rest_server, daemon=True)
    rest_thread.start()
    
    # Lancer MCP en principal
    mcp.run(transport="sse")
