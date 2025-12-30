"""
Module de Contexte Dynamique pour AI Orchestrator
Récupère l'état réel du système pour l'injecter dans le prompt
Version SÉCURISÉE: Utilise run_command_async (pas de shell=True)
"""

import asyncio

import psutil

# Import local pour utiliser la version sécurisée
from utils.async_subprocess import run_command_async


async def get_docker_context() -> str:
    """Récupère les conteneurs Docker actifs (Async & Secure)"""
    try:
        # Commande sous forme de liste pour éviter shell=True implicite
        # Note: run_command_async gère les listes via exec
        cmd = ["docker", "ps", "--format", "{{.Names}} ({{.Image}}) - {{.Status}}"]
        output, code = await run_command_async(cmd, timeout=5)

        if code == 0 and output.strip():
            return f"## 🐳 Conteneurs Actifs\n{output.strip()}"
        return "## 🐳 Docker\nAucun conteneur actif ou erreur d'accès."
    except Exception as e:
        return f"## 🐳 Docker\nErreur: {str(e)}"


def get_system_resources() -> str:
    """Récupère l'utilisation des ressources (Synchrone car psutil est rapide)"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return f"""## 🖥️Ressources Système
- CPU: {cpu_percent}%
- RAM: {memory.percent}% ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)
- Disque (/): {disk.percent}% utilisé"""
    except Exception:
        return "## 🖥️Ressources\nNon disponible"


async def get_active_services() -> str:
    """Vérifie quelques services clés (Async & Secure)"""
    services = ["ollama", "docker", "nginx"]
    status_lines = []

    for svc in services:
        try:
            # Commande directe sans shell
            cmd = ["systemctl", "is-active", svc]
            output, code = await run_command_async(cmd, timeout=2)
            status = "✅ Actif" if code == 0 else "❌ Inactif"
            status_lines.append(f"- {svc}: {status}")
        except:
            pass

    if status_lines:
        return "## ⚙️ Services Système\n" + "\n".join(status_lines)
    return ""


async def get_dynamic_context() -> str:
    """Assemble tout le contexte dynamique (Async)"""
    # Exécuter les tâches async en parallèle
    docker_task = get_docker_context()
    services_task = get_active_services()

    # psutil est synchrone, on l'appelle directement
    resources = get_system_resources()

    # Attendre les résultats async
    docker, services = await asyncio.gather(docker_task, services_task)

    sections = [resources, services, docker]
    return "\n\n".join(sections)


# Flag pour indiquer que le module est chargé
DYNAMIC_CONTEXT_ENABLED = True
