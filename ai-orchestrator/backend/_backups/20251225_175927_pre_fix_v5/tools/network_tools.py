"""
Outils réseau et UDM pour AI Orchestrator v4.0
- check_url
- udm_status
- udm_clients
- network_scan
"""

import os
from tools import register_tool
from utils.async_subprocess import run_command_async, run_ssh_command

# Configuration UDM
UDM_HOST = os.getenv("UDM_HOST", "10.10.10.1")
UDM_SSH_KEY = os.getenv("UDM_SSH_KEY", "/home/lalpha/.ssh/id_rsa_udm")


@register_tool("check_url")
async def check_url(params: dict) -> str:
    """Vérifier la disponibilité d'une URL"""
    url = params.get("url", "")
    
    if not url:
        return "Erreur: URL requise"
    
    # Ajouter http:// si pas de protocole
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    
    output, code = await run_command_async(
        f"curl -sI -o /dev/null -w '%{{http_code}} %{{time_total}}s' --connect-timeout 10 '{url}'",
        timeout=15
    )
    
    if code == 0 and output.strip():
        parts = output.strip().split()
        http_code = parts[0] if parts else "?"
        time_total = parts[1] if len(parts) > 1 else "?"
        
        status = "✅" if http_code.startswith("2") else "⚠️" if http_code.startswith("3") else "❌"
        return f"{status} {url}\nCode HTTP: {http_code}\nTemps: {time_total}"
    
    return f"❌ Impossible de joindre {url}"


@register_tool("udm_status")
async def udm_status(params: dict) -> str:
    """Obtenir le statut du UDM-Pro"""
    commands = {
        "uptime": "uptime",
        "memory": "free -h",
        "disk": "df -h /",
        "temperature": "cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo 'N/A'"
    }
    
    results = []
    for name, cmd in commands.items():
        output, code = await run_ssh_command(
            UDM_HOST, cmd, key_path=UDM_SSH_KEY, timeout=10
        )
        results.append(f"=== {name.upper()} ===\n{output}")
    
    return f"Statut UDM-Pro ({UDM_HOST}):\n" + "\n".join(results)


@register_tool("udm_clients")
async def udm_clients(params: dict) -> str:
    """Lister les clients connectés au UDM"""
    # Utilise l'API UniFi ou une commande SSH
    output, code = await run_ssh_command(
        UDM_HOST,
        "cat /data/unifi-core/config/clients.list 2>/dev/null || ip neigh | head -30",
        key_path=UDM_SSH_KEY,
        timeout=15
    )
    
    return f"Clients UDM-Pro:\n{output}"


@register_tool("network_interfaces")
async def network_interfaces(params: dict) -> str:
    """Lister les interfaces réseau"""
    output, code = await run_command_async(
        "ip -br addr",
        timeout=10
    )
    
    return f"Interfaces réseau:\n{output}"


@register_tool("port_scan")
async def port_scan(params: dict) -> str:
    """Scanner les ports ouverts sur une machine"""
    host = params.get("host", "localhost")
    
    # Utiliser ss pour localhost, nmap si disponible pour autres hôtes
    if host in ["localhost", "127.0.0.1"]:
        output, code = await run_command_async(
            "ss -tlnp",
            timeout=10
        )
    else:
        output, code = await run_command_async(
            f"nmap -F {host} 2>/dev/null || nc -zv {host} 22 80 443 2>&1",
            timeout=30
        )
    
    return f"Ports ouverts ({host}):\n{output}"


@register_tool("dns_lookup")
async def dns_lookup(params: dict) -> str:
    """Résolution DNS"""
    domain = params.get("domain", "")
    
    if not domain:
        return "Erreur: domaine requis"
    
    output, code = await run_command_async(
        f"dig +short {domain} && dig +short {domain} MX",
        timeout=10
    )
    
    return f"DNS pour {domain}:\n{output}"
