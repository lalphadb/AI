"""
Outils réseau pour AI Orchestrator v5.0
- check_url
- network_interfaces
- udm_status
- udm_clients
- udm_network_info
"""

import os
import logging
import httpx
from tools import register_tool
from utils.async_subprocess import run_command_async

logger = logging.getLogger(__name__)

# Configuration UDM
UDM_HOST = os.getenv("UDM_HOST", "192.168.1.1")
UDM_USER = os.getenv("UDM_USER", "root")
SSH_KEY = os.getenv("UDM_SSH_KEY", "/home/lalpha/.ssh/id_rsa_udm")


@register_tool("check_url")
async def check_url(params: dict) -> str:
    """Vérifier l'accessibilité d'une URL"""
    url = params.get("url", "")
    
    if not url:
        return "Erreur: url requise"
    
    # Ajouter le protocole si manquant
    if not url.startswith(('http://', 'https://')):
        url = f"https://{url}"
    
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url)
            
            return f"""🌐 Vérification {url}:
  Status: {response.status_code}
  Temps: {response.elapsed.total_seconds():.2f}s
  Headers: Content-Type={response.headers.get('content-type', 'N/A')}
  Taille: {len(response.content)} bytes"""
            
    except httpx.ConnectTimeout:
        return f"❌ Timeout connexion: {url}"
    except httpx.ConnectError as e:
        return f"❌ Erreur connexion: {url} - {str(e)}"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"


@register_tool("network_interfaces")
async def network_interfaces(params: dict) -> str:
    """Lister les interfaces réseau locales"""
    output, code = await run_command_async(
        "ip -br addr show",
        timeout=10
    )
    
    if code != 0:
        return f"❌ Erreur: {output}"
    
    return f"🔌 Interfaces réseau:\n{output}"


async def ssh_udm(command: str) -> tuple:
    """Exécuter une commande SSH sur l'UDM"""
    ssh_cmd = f"ssh -i {SSH_KEY} -o StrictHostKeyChecking=no -o ConnectTimeout=10 {UDM_USER}@{UDM_HOST} '{command}'"
    return await run_command_async(ssh_cmd, timeout=30)


@register_tool("udm_status")
async def udm_status(params: dict) -> str:
    """Obtenir le statut de l'UDM-Pro"""
    output, code = await ssh_udm("uptime && free -h && df -h / /data 2>/dev/null")
    
    if code != 0:
        return f"❌ Connexion UDM échouée: {output}"
    
    return f"📡 UDM-Pro Status:\n{output}"


@register_tool("udm_clients")
async def udm_clients(params: dict) -> str:
    """Lister les clients connectés sur l'UDM"""
    # Essayer de récupérer les clients via l'API REST ou les commandes
    output, code = await ssh_udm("cat /data/unifi-core/config/settings.json 2>/dev/null | grep -o 'client_count.*' | head -1 || echo 'Info clients non disponible'")
    
    if code != 0:
        return f"❌ Erreur récupération clients: {output}"
    
    # Alternative: compter les baux DHCP
    dhcp_output, _ = await ssh_udm("wc -l /run/dnsmasq.leases 2>/dev/null || echo '0'")
    
    return f"📱 Clients UDM:\n{output}\nBaux DHCP actifs: {dhcp_output.strip()}"


@register_tool("udm_network_info")
async def udm_network_info(params: dict) -> str:
    """Informations réseau de l'UDM"""
    commands = """
echo '=== INTERFACES ==='
ip -br addr show | head -10
echo ''
echo '=== VLANs ==='
brctl show 2>/dev/null | head -10 || echo 'N/A'
echo ''
echo '=== ROUTES ==='
ip route show | head -10
"""
    
    output, code = await ssh_udm(commands)
    
    if code != 0:
        return f"❌ Erreur info réseau: {output}"
    
    return f"🌐 UDM Network Info:\n{output}"


@register_tool("dns_lookup")
async def dns_lookup(params: dict) -> str:
    """Résolution DNS"""
    host = params.get("host", "")
    
    if not host:
        return "Erreur: host requis"
    
    # Sanitizer le host
    if not all(c.isalnum() or c in '.-' for c in host):
        return "❌ Nom d'hôte invalide"
    
    output, code = await run_command_async(f"nslookup {host}", timeout=10)
    
    if code != 0:
        return f"❌ Résolution échouée: {output}"
    
    return f"🔍 DNS Lookup {host}:\n{output}"


@register_tool("ping_host")
async def ping_host(params: dict) -> str:
    """Ping un hôte"""
    host = params.get("host", "")
    count = params.get("count", 3)
    
    if not host:
        return "Erreur: host requis"
    
    # Sanitizer
    if not all(c.isalnum() or c in '.-:' for c in host):
        return "❌ Hôte invalide"
    
    try:
        count = min(int(count), 10)
    except:
        count = 3
    
    output, code = await run_command_async(f"ping -c {count} {host}", timeout=20)
    
    status = "✅" if code == 0 else "❌"
    return f"{status} Ping {host}:\n{output}"
