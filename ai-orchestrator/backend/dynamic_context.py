"""
Module de Contexte Dynamique pour AI Orchestrator
Récupère l'état réel du système pour l'injecter dans le prompt
"""

import subprocess
import psutil
import json
import os

def get_docker_context() -> str:
    """Récupère les conteneurs Docker actifs"""
    try:
        # Lister les conteneurs avec leur image et statut
        cmd = "docker ps --format '{{.Names}} ({{.Image}}) - {{.Status}}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            return f"## 🐳 Conteneurs Actifs\n{result.stdout.strip()}"
        return "## 🐳 Docker\nAucun conteneur actif ou erreur d'accès."
    except Exception as e:
        return f"## 🐳 Docker\nErreur: {str(e)}"

def get_system_resources() -> str:
    """Récupère l'utilisation des ressources"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return f"""## 🖥️ Ressources Système
- CPU: {cpu_percent}%
- RAM: {memory.percent}% ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)
- Disque (/): {disk.percent}% utilisé"""
    except Exception:
        return "## 🖥️ Ressources\nNon disponible"

def get_active_services() -> str:
    """Vérifie quelques services clés"""
    services = ["ollama", "docker", "nginx"]
    status_lines = []
    for svc in services:
        try:
            cmd = f"systemctl is-active {svc}"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            status = "✅ Actif" if res.returncode == 0 else "❌ Inactif"
            status_lines.append(f"- {svc}: {status}")
        except:
            pass
    
    if status_lines:
        return "## ⚙️ Services Système\n" + "\n".join(status_lines)
    return ""

def get_dynamic_context() -> str:
    """Assemble tout le contexte dynamique"""
    sections = [
        get_system_resources(),
        get_active_services(),
        get_docker_context()
    ]
    return "\n\n".join(sections)
