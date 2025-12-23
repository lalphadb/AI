#!/usr/bin/env python3
"""
MCP Server 4LB.ca v2.1 - Accès complet pour Gemini + REST API
Outils de lecture, écriture, modification et administration
Supporte MCP (SSE) ET REST API directe
"""

from mcp.server.fastmcp import FastMCP
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import subprocess
import os
import shutil
import uvicorn
from datetime import datetime
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

HOST = "0.0.0.0"
PORT = 8888

# Chemins autorisés pour lecture/écriture
ALLOWED_PATHS = [
    "/home/lalpha/projets",
    "/home/lalpha/scripts",
    "/home/lalpha/documentation",
    "/tmp"
]

# Chemins interdits
FORBIDDEN_PATHS = [".env", "id_rsa", "id_ed25519", ".ssh/", "secrets", ".git/objects"]
FORBIDDEN_EXTENSIONS = [".key", ".pem", ".p12"]

def is_path_allowed(path: str, write: bool = False) -> tuple[bool, str]:
    """Vérifie si un chemin est autorisé"""
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
# APPLICATION FASTAPI + MCP
# ============================================================

app = FastAPI(title="4LB MCP Server v2.1", description="MCP + REST API")

# CORS pour accès externe
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# MCP Server
mcp = FastMCP("4LB-Admin-Server-v2", host=HOST, port=PORT)

# ============================================================
# MODÈLES PYDANTIC POUR REST API
# ============================================================

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

class CommandRequest(BaseModel):
    command: str
    cwd: str = "/home/lalpha"

class GitCommitRequest(BaseModel):
    repo_path: str
    message: str
    add_all: bool = True

# ============================================================
# FONCTIONS OUTILS (partagées entre MCP et REST)
# ============================================================

def _get_gpu_status() -> str:
    try:
        result = subprocess.check_output([
            "nvidia-smi", 
            "--query-gpu=name,utilization.gpu,memory.total,memory.used,memory.free,temperature.gpu,power.draw",
            "--format=csv,noheader"
        ])
        data = result.decode().strip().split(", ")
        return f"""🎮 GPU Status:
- Modèle: {data[0]}
- Utilisation: {data[1]}%
- VRAM: {data[3]} / {data[2]} ({data[4]} libre)
- Température: {data[5]}°C
- Consommation: {data[6]}W"""
    except Exception as e:
        return f"❌ Erreur GPU: {str(e)}"

def _get_system_status() -> str:
    try:
        cpu = subprocess.check_output(["nproc"]).decode().strip()
        load = subprocess.check_output(["cat", "/proc/loadavg"]).decode().strip()
        mem = subprocess.check_output(["free", "-h", "--si"]).decode()
        disk = subprocess.check_output(["df", "-h", "/"]).decode()
        uptime = subprocess.check_output(["uptime", "-p"]).decode().strip()
        return f"""🖥️ System Status:
- CPU Cores: {cpu}
- Load: {load}
- Uptime: {uptime}

📊 Mémoire:
{mem}

💾 Disque:
{disk}"""
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

def _get_docker_status(all_containers: bool = False) -> str:
    try:
        cmd = ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"]
        if all_containers:
            cmd.insert(2, "-a")
        result = subprocess.check_output(cmd)
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
        size = os.path.getsize(abs_path)
        return f"📄 {abs_path} ({size} bytes):\n\n{content}"
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

def _list_directory(path: str, recursive: bool = False) -> str:
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
# OUTILS MCP (décorateurs @mcp.tool)
# ============================================================

@mcp.tool()
def get_gpu_status() -> str:
    """Récupère l'état du GPU NVIDIA."""
    return _get_gpu_status()

@mcp.tool()
def get_system_status() -> str:
    """État système (CPU, RAM, Disk, Load)."""
    return _get_system_status()

@mcp.tool()
def get_docker_status(all_containers: bool = False) -> str:
    """Liste les containers Docker."""
    return _get_docker_status(all_containers)

@mcp.tool()
def read_file(path: str, lines: int = 0) -> str:
    """Lire un fichier. lines=0 pour tout."""
    return _read_file(path, lines)

@mcp.tool()
def write_file(path: str, content: str, backup: bool = True) -> str:
    """Écrire un fichier avec backup automatique."""
    return _write_file(path, content, backup)

@mcp.tool()
def patch_file(path: str, old_text: str, new_text: str, backup: bool = True) -> str:
    """Modifier du texte dans un fichier (search/replace)."""
    return _patch_file(path, old_text, new_text, backup)

@mcp.tool()
def list_directory(path: str, recursive: bool = False) -> str:
    """Lister un répertoire."""
    return _list_directory(path, recursive)

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
# ENDPOINTS REST API (pour accès HTTP direct)
# ============================================================

@app.get("/")
def root():
    return {"server": "4LB MCP Server v2.1", "status": "running", "mcp": "/sse", "api": "/api/*"}

@app.get("/api/status")
def api_status():
    return {"gpu": _get_gpu_status(), "system": _get_system_status(), "docker": _get_docker_status()}

@app.get("/api/gpu")
def api_gpu():
    return {"result": _get_gpu_status()}

@app.get("/api/system")
def api_system():
    return {"result": _get_system_status()}

@app.get("/api/docker")
def api_docker():
    return {"result": _get_docker_status()}

@app.post("/api/read_file")
def api_read_file(req: FileReadRequest):
    return {"result": _read_file(req.path, req.lines)}

@app.post("/api/write_file")
def api_write_file(req: FileWriteRequest):
    return {"result": _write_file(req.path, req.content, req.backup)}

@app.post("/api/patch_file")
def api_patch_file(req: FilePatchRequest):
    return {"result": _patch_file(req.path, req.old_text, req.new_text, req.backup)}

@app.post("/api/run_command")
def api_run_command(req: CommandRequest):
    return {"result": _run_command(req.command, req.cwd)}

@app.get("/api/list/{path:path}")
def api_list(path: str):
    return {"result": _list_directory(f"/{path}")}

@app.get("/api/docker/logs/{container}")
def api_docker_logs(container: str, lines: int = 50):
    return {"result": _docker_logs(container, lines)}

@app.post("/api/docker/restart/{container}")
def api_docker_restart(container: str):
    return {"result": _docker_restart(container)}

@app.get("/api/git/status")
def api_git_status(repo: str = "/home/lalpha/projets"):
    return {"result": _git_status(repo)}

@app.post("/api/git/commit")
def api_git_commit(req: GitCommitRequest):
    return {"result": _git_commit(req.repo_path, req.message, req.add_all)}

@app.get("/api/python/check/{path:path}")
def api_python_check(path: str):
    return {"result": _python_check_syntax(f"/{path}")}

# ============================================================
# POINT D'ENTRÉE
# ============================================================

if __name__ == "__main__":
    print("🚀 MCP Server 4LB v2.1 - Démarrage...")
    print(f"📡 MCP SSE: http://{HOST}:{PORT}/sse")
    print(f"🌐 REST API: http://{HOST}:{PORT}/api/*")
    print(f"📁 Chemins autorisés: {ALLOWED_PATHS}")
    
    # Lancer avec les deux interfaces
    # Note: FastMCP gère /sse, FastAPI gère le reste
    mcp.run(transport="sse")
