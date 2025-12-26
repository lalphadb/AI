"""
Outils Docker pour AI Orchestrator v4.0
- docker_status
- docker_logs
- docker_restart
- docker_compose
"""

import re
from tools import register_tool
from utils.async_subprocess import run_command_async

def sanitize_container_name(name: str) -> str:
    """
    Valide et nettoie un nom de conteneur Docker.
    Noms valides: lettres, chiffres, underscores, tirets, points.
    Doit commencer par une lettre ou un chiffre.
    """
    if not name:
        raise ValueError("Container name cannot be empty")
    
    # Pattern Docker officiel pour les noms
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$', name):
        raise ValueError(f"Invalid container name: {name}")
    
    # Longueur max
    if len(name) > 128:
        raise ValueError(f"Container name too long: {len(name)} > 128")
    
    return name


@register_tool("docker_status")
async def docker_status(params: dict) -> str:
    """Liste des conteneurs Docker avec leur statut"""
    output, code = await run_command_async(
        "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'",
        timeout=30
    )
    return f"Conteneurs Docker:\n{output}"


@register_tool("docker_logs")
async def docker_logs(params: dict) -> str:
    """Obtenir les logs d'un conteneur Docker"""
    container = params.get("container", "")
    lines = params.get("lines", 50)
    
    if not container:
        return "Erreur: nom du conteneur requis"
    
    # Sanitization
    try:
        container = sanitize_container_name(container)
    except ValueError as e:
        return f"❌ {str(e)}"
    
    # Validation du nombre de lignes
    try:
        lines = min(int(lines), 500)  # Max 500 lignes
    except (ValueError, TypeError):
        lines = 50
    
    output, code = await run_command_async(
        f"docker logs --tail {lines} {container} 2>&1",
        timeout=30
    )
    return f"Logs de {container} (dernières {lines} lignes):\n{output}"


@register_tool("docker_restart")
async def docker_restart(params: dict) -> str:
    """Redémarrer un conteneur Docker"""
    container = params.get("container", "")
    
    if not container:
        return "Erreur: nom du conteneur requis"
    
    # Sanitization
    try:
        container = sanitize_container_name(container)
    except ValueError as e:
        return f"❌ {str(e)}"
    
    output, code = await run_command_async(
        f"docker restart {container}",
        timeout=60
    )
    
    status = "✅" if code == 0 else "❌"
    return f"{status} Redémarrage de {container}: {output}"


@register_tool("docker_compose")
async def docker_compose(params: dict) -> str:
    """Exécuter une commande docker compose"""
    action = params.get("action", "")
    path = params.get("path", "")
    
    valid_actions = ["up", "down", "restart", "ps", "logs", "build", "pull"]
    if action not in valid_actions:
        return f"Erreur: action invalide '{action}'. Valides: {', '.join(valid_actions)}"
    
    # Construire la commande
    cmd = "docker compose"
    if path:
        cmd = f"cd {path} && {cmd}"
    
    # Options selon l'action
    if action == "up":
        cmd += " up -d"
    elif action == "logs":
        cmd += " logs --tail 50"
    else:
        cmd += f" {action}"
    
    output, code = await run_command_async(cmd, timeout=120)
    
    status = "✅" if code == 0 else "❌"
    return f"{status} docker compose {action}:\n{output}"


@register_tool("docker_exec")
async def docker_exec(params: dict) -> str:
    """Exécuter une commande dans un conteneur"""
    container = params.get("container", "")
    command = params.get("command", "")
    
    if not container or not command:
        return "Erreur: container et command requis"
    
    # Sanitization
    try:
        container = sanitize_container_name(container)
    except ValueError as e:
        return f"❌ {str(e)}"
    
    output, code = await run_command_async(
        f"docker exec {container} {command}",
        timeout=60
    )
    
    return f"Commande dans {container}:\n{output}"


@register_tool("docker_stats")
async def docker_stats(params: dict) -> str:
    """Statistiques des conteneurs Docker"""
    output, code = await run_command_async(
        "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'",
        timeout=15
    )
    return f"Statistiques Docker:\n{output}"
