"""
🚀 API REST - Orchestrateur 4LB

Endpoints:
- GET /health - Status de l'API
- GET /tools - Liste des outils disponibles
- POST /execute - Exécuter un outil
- GET /metrics - Métriques système
- GET /backups - Liste des sauvegardes
- POST /gitops/{action} - Actions GitOps
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from config.settings import SERVER_HOST, SERVER_PORT, LOG_LEVEL
from modules import (
    base_tools, gitops_tools, backup_tools, self_improve_tools,
    TOOLS_CATALOG, get_tool_count
)

# Configuration logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)

# Créer l'application FastAPI
app = FastAPI(
    title="🎛️ Orchestrateur 4LB",
    description="API de gestion intelligente de l'infrastructure",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Modèles Pydantic ===

class ExecuteRequest(BaseModel):
    tool: str
    params: Optional[Dict[str, Any]] = {}

class GitOpsRequest(BaseModel):
    path: Optional[str] = None
    message: Optional[str] = None
    target: Optional[str] = None

class BackupRequest(BaseModel):
    type: str = "full"
    include_secrets: bool = False


# === Routes ===

@app.get("/")
async def root():
    """Page d'accueil"""
    return {
        "name": "🎛️ Orchestrateur 4LB",
        "version": "1.0.0",
        "tools_count": get_tool_count(),
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "tools": "/tools",
            "execute": "/execute",
            "metrics": "/metrics"
        }
    }


@app.get("/health")
async def health():
    """Vérification de santé"""
    # Tester Ollama
    ollama_status = self_improve_tools.test_ollama_connection()
    
    # Tester Docker
    docker_status = base_tools.docker_status()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "api": "ok",
            "ollama": "ok" if ollama_status.get("success") else "error",
            "docker": "ok" if docker_status.get("success") else "error"
        },
        "details": {
            "ollama": ollama_status,
            "docker_containers": docker_status.get("count", 0)
        }
    }


@app.get("/tools")
async def list_tools():
    """Liste tous les outils disponibles"""
    return {
        "total": get_tool_count(),
        "catalog": TOOLS_CATALOG
    }


@app.post("/execute")
async def execute_tool(request: ExecuteRequest):
    """
    Exécuter un outil
    
    Exemples:
    - {"tool": "docker_status"}
    - {"tool": "read_file", "params": {"path": "/etc/hostname"}}
    - {"tool": "gitops_status"}
    """
    tool_name = request.tool
    params = request.params or {}
    
    # Mapper les outils
    tool_mapping = {
        # Base
        "read_file": base_tools.read_file,
        "write_file": base_tools.write_file,
        "propose_diff": base_tools.propose_diff,
        "apply_diff": base_tools.apply_diff,
        "run_command": base_tools.run_command,
        "list_directory": base_tools.list_directory,
        "file_exists": base_tools.file_exists,
        "get_system_info": base_tools.get_system_info,
        "docker_status": base_tools.docker_status,
        "list_pending_diffs": base_tools.list_pending_diffs,
        
        # GitOps
        "gitops_init": gitops_tools.gitops_init,
        "gitops_status": gitops_tools.gitops_status,
        "gitops_commit": gitops_tools.gitops_commit,
        "gitops_rollback": gitops_tools.gitops_rollback,
        "gitops_setup_hooks": gitops_tools.gitops_setup_hooks,
        "gitops_log": gitops_tools.gitops_log,
        
        # Backup
        "backup_postgres": backup_tools.backup_postgres,
        "backup_configs": backup_tools.backup_configs,
        "backup_ollama_models": backup_tools.backup_ollama_models,
        "backup_full": backup_tools.backup_full,
        "backup_s3": backup_tools.backup_s3,
        "list_backups": backup_tools.list_backups,
        "cleanup_old_backups": backup_tools.cleanup_old_backups,
        
        # Self-Improve
        "self_improve_analyze_logs": self_improve_tools.self_improve_analyze_logs,
        "self_improve_anomalies": self_improve_tools.self_improve_anomalies,
        "self_improve_suggestions": self_improve_tools.self_improve_suggestions,
        "test_ollama": self_improve_tools.test_ollama_connection,
    }
    
    if tool_name not in tool_mapping:
        raise HTTPException(
            status_code=404, 
            detail=f"Outil '{tool_name}' non trouvé. Utilisez /tools pour voir la liste."
        )
    
    try:
        # Exécuter l'outil
        result = tool_mapping[tool_name](**params)
        
        return {
            "tool": tool_name,
            "params": params,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur exécution {tool_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def get_metrics():
    """Obtenir les métriques système"""
    system_info = base_tools.get_system_info()
    docker_info = base_tools.docker_status()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "system": system_info.get("info", {}),
        "docker": {
            "running": docker_info.get("running", 0),
            "total": docker_info.get("count", 0)
        }
    }


@app.get("/backups")
async def list_backups(backup_type: Optional[str] = None):
    """Lister les sauvegardes"""
    return backup_tools.list_backups(backup_type)


@app.post("/backup")
async def create_backup(request: BackupRequest, background_tasks: BackgroundTasks):
    """Créer une sauvegarde"""
    if request.type == "full":
        result = backup_tools.backup_full(include_secrets=request.include_secrets)
    elif request.type == "postgres":
        result = backup_tools.backup_postgres()
    elif request.type == "configs":
        result = backup_tools.backup_configs(include_secrets=request.include_secrets)
    elif request.type == "ollama":
        result = backup_tools.backup_ollama_models()
    else:
        raise HTTPException(status_code=400, detail=f"Type de backup invalide: {request.type}")
    
    return result


@app.get("/gitops/status")
async def gitops_status(path: Optional[str] = None):
    """Statut GitOps"""
    return gitops_tools.gitops_status(path)


@app.post("/gitops/commit")
async def gitops_commit(request: GitOpsRequest):
    """Commit GitOps"""
    if not request.message:
        raise HTTPException(status_code=400, detail="Message de commit requis")
    return gitops_tools.gitops_commit(request.message, request.path)


@app.post("/gitops/rollback")
async def gitops_rollback(request: GitOpsRequest):
    """Rollback GitOps"""
    target = request.target or "HEAD~1"
    return gitops_tools.gitops_rollback(target, request.path)


@app.get("/gitops/log")
async def gitops_log(path: Optional[str] = None, limit: int = 10):
    """Historique GitOps"""
    return gitops_tools.gitops_log(path, limit)


@app.get("/analyze")
async def analyze_system():
    """Analyser le système avec IA"""
    return self_improve_tools.self_improve_anomalies()


@app.post("/analyze/logs")
async def analyze_logs(source: str = "docker", focus: Optional[str] = None):
    """Analyser les logs avec IA"""
    return self_improve_tools.self_improve_analyze_logs(source, focus)


@app.get("/suggestions")
async def get_suggestions(context: Optional[str] = None):
    """Obtenir des suggestions d'amélioration"""
    return self_improve_tools.self_improve_suggestions(context)


# === Point d'entrée ===

def run_server():
    """Démarrer le serveur"""
    import uvicorn
    
    logger.info(f"🚀 Démarrage Orchestrateur 4LB sur {SERVER_HOST}:{SERVER_PORT}")
    
    uvicorn.run(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level=LOG_LEVEL.lower()
    )


if __name__ == "__main__":
    run_server()
