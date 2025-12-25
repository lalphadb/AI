"""
Outils système pour AI Orchestrator v4.0
- execute_command
- system_info
- service_status
- service_control
- disk_usage
"""

from tools import register_tool
from utils.async_subprocess import run_command_async, run_multiple_commands


@register_tool("execute_command")
async def execute_command(params: dict, security_validator=None, audit_logger=None) -> str:
    """Exécuter une commande Linux avec validation de sécurité"""
    cmd = params.get("command", "")
    if not cmd:
        return "Erreur: commande vide"
    
    # Validation de sécurité si disponible
    if security_validator:
        allowed, reason = security_validator(cmd)
        if audit_logger:
            audit_logger.log_command(cmd, allowed=allowed, reason=reason)
        if not allowed:
            return f"🚫 Commande bloquée: {reason}"
    
    output, code = await run_command_async(cmd, timeout=60)
    return f"Commande: {cmd}\nCode retour: {code}\nSortie:\n{output[:3000]}"


@register_tool("system_info")
async def system_info(params: dict) -> str:
    """Obtenir les informations système complètes"""
    commands = {
        "hostname": "hostname",
        "uptime": "uptime",
        "cpu": "lscpu | head -20",
        "memory": "free -h",
        "disk": "df -h /",
        "gpu": "nvidia-smi --query-gpu=name,memory.total,memory.used,temperature.gpu --format=csv,noheader 2>/dev/null || echo 'Pas de GPU détecté'",
        "load": "cat /proc/loadavg"
    }
    
    results = await run_multiple_commands(commands, timeout=10)
    
    output_lines = []
    for name, output in results.items():
        output_lines.append(f"=== {name.upper()} ===\n{output}")
    
    return "\n".join(output_lines)


@register_tool("service_status")
async def service_status(params: dict) -> str:
    """Obtenir le statut d'un service systemd"""
    service = params.get("service", "")
    if not service:
        return "Erreur: nom du service requis"
    
    output, code = await run_command_async(
        f"systemctl status {service} --no-pager",
        timeout=10
    )
    return f"Statut de {service}:\n{output}"


@register_tool("service_control")
async def service_control(params: dict) -> str:
    """Contrôler un service systemd (start/stop/restart)"""
    service = params.get("service", "")
    action = params.get("action", "")
    
    if not service:
        return "Erreur: nom du service requis"
    if action not in ["start", "stop", "restart", "reload", "enable", "disable"]:
        return f"Erreur: action invalide '{action}'. Valides: start, stop, restart, reload, enable, disable"
    
    output, code = await run_command_async(
        f"sudo systemctl {action} {service}",
        timeout=30
    )
    
    status = "✅" if code == 0 else "❌"
    return f"{status} Action '{action}' sur {service}:\n{output or 'OK'}"


@register_tool("disk_usage")
async def disk_usage(params: dict) -> str:
    """Analyser l'utilisation du disque"""
    path = params.get("path", "/")
    
    commands = {
        "df": f"df -h {path}",
        "du": f"du -sh {path}/* 2>/dev/null | sort -rh | head -20"
    }
    
    results = await run_multiple_commands(commands, timeout=30)
    
    return f"Espace disque pour {path}:\n{results.get('df', '')}\n\nDétail:\n{results.get('du', '')}"
