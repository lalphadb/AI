"""
Module Tools pour AI Orchestrator v4.0
Découpage modulaire de execute_tool

Usage:
    from tools import execute_tool, TOOLS_DEFINITIONS
    result = await execute_tool("docker_status", {})
"""

from typing import Dict, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)

# Registre des handlers d'outils
_tool_handlers: Dict[str, Callable] = {}
_handlers_loaded = False


def register_tool(name: str):
    """Décorateur pour enregistrer un handler d'outil"""
    def decorator(func: Callable):
        _tool_handlers[name] = func
        return func
    return decorator


def _ensure_handlers_loaded():
    """Charge les handlers si pas encore fait"""
    global _handlers_loaded
    if _handlers_loaded:
        return
    
    # Import des modules d'outils (doit être après la définition de register_tool)
    from tools import system_tools
    from tools import docker_tools
    from tools import file_tools
    from tools import git_tools
    from tools import network_tools
    from tools import memory_tools
    from tools import ai_tools
    
    _handlers_loaded = True
    logger.info(f"✅ {len(_tool_handlers)} outils chargés")


async def execute_tool(
    tool_name: str, 
    params: dict,
    uploaded_files: dict = None,
    security_validator = None,
    audit_logger = None
) -> str:
    """
    Point d'entrée principal pour l'exécution des outils.
    Dispatch vers le bon handler selon le nom de l'outil.
    """
    _ensure_handlers_loaded()
    
    if tool_name not in _tool_handlers:
        available = ", ".join(sorted(_tool_handlers.keys())[:10])
        return f"❌ Outil inconnu: {tool_name}. Disponibles: {available}..."
    
    try:
        handler = _tool_handlers[tool_name]
        
        # Appeler le handler avec les bons arguments selon l'outil
        if tool_name in ['read_file', 'write_file', 'execute_command']:
            return await handler(
                params, 
                security_validator=security_validator,
                audit_logger=audit_logger
            )
        elif tool_name == 'analyze_image':
            return await handler(params, uploaded_files=uploaded_files)
        else:
            return await handler(params)
            
    except Exception as e:
        logger.error(f"Erreur exécution {tool_name}: {e}")
        return f"❌ Erreur {tool_name}: {str(e)}"


# Définitions des outils (pour le prompt)
TOOLS_DEFINITIONS = [
    # === Système ===
    {"name": "execute_command", "description": "Exécuter une commande Linux", "parameters": {"command": "str"}},
    {"name": "system_info", "description": "Obtenir les infos système (CPU, RAM, Disk, GPU)", "parameters": {}},
    {"name": "service_status", "description": "Statut d'un service systemd", "parameters": {"service": "str"}},
    {"name": "service_control", "description": "Contrôler un service (start/stop/restart)", "parameters": {"service": "str", "action": "str"}},
    {"name": "disk_usage", "description": "Analyser l'utilisation disque", "parameters": {"path": "str (optionnel)"}},
    
    # === Docker ===
    {"name": "docker_status", "description": "Liste des conteneurs Docker", "parameters": {}},
    {"name": "docker_logs", "description": "Logs d'un conteneur", "parameters": {"container": "str", "lines": "int (optionnel)"}},
    {"name": "docker_restart", "description": "Redémarrer un conteneur", "parameters": {"container": "str"}},
    {"name": "docker_compose", "description": "Commande docker compose", "parameters": {"action": "str", "path": "str (optionnel)"}},
    {"name": "docker_stats", "description": "Statistiques CPU/RAM des conteneurs", "parameters": {}},
    
    # === Fichiers ===
    {"name": "read_file", "description": "Lire un fichier", "parameters": {"path": "str"}},
    {"name": "write_file", "description": "Écrire un fichier", "parameters": {"path": "str", "content": "str"}},
    {"name": "list_directory", "description": "Lister un répertoire", "parameters": {"path": "str", "recursive": "bool (optionnel)"}},
    {"name": "search_files", "description": "Rechercher des fichiers", "parameters": {"pattern": "str", "path": "str (optionnel)"}},
    
    # === Git ===
    {"name": "git_status", "description": "État d'un dépôt Git", "parameters": {"path": "str"}},
    {"name": "git_diff", "description": "Diff Git", "parameters": {"path": "str"}},
    {"name": "git_log", "description": "Historique Git", "parameters": {"path": "str", "count": "int (optionnel)"}},
    {"name": "git_pull", "description": "Pull Git", "parameters": {"path": "str"}},
    
    # === Réseau / UDM ===
    {"name": "check_url", "description": "Vérifier une URL", "parameters": {"url": "str"}},
    {"name": "udm_status", "description": "Statut UDM-Pro", "parameters": {}},
    {"name": "udm_clients", "description": "Clients connectés UDM", "parameters": {}},
    {"name": "network_interfaces", "description": "Interfaces réseau locales", "parameters": {}},
    
    # === Mémoire ===
    {"name": "memory_store", "description": "Stocker en mémoire sémantique", "parameters": {"key": "str", "value": "str", "category": "str (optionnel)"}},
    {"name": "memory_recall", "description": "Rappeler de la mémoire", "parameters": {"query": "str", "limit": "int (optionnel)"}},
    {"name": "memory_list", "description": "Lister tous les souvenirs", "parameters": {"category": "str (optionnel)"}},
    
    # === IA ===
    {"name": "analyze_image", "description": "Analyser une image avec vision", "parameters": {"query": "str"}},
    {"name": "create_plan", "description": "Créer un plan d'action", "parameters": {"objective": "str", "constraints": "str (optionnel)"}},
    {"name": "final_answer", "description": "Réponse finale à l'utilisateur", "parameters": {"answer": "str"}},
]


def get_tools_description() -> str:
    """Génère la description des outils pour le prompt système"""
    lines = []
    for tool in TOOLS_DEFINITIONS:
        params = ", ".join([f"{k}: {v}" for k, v in tool.get("parameters", {}).items()])
        if params:
            lines.append(f"- {tool['name']}({params}): {tool['description']}")
        else:
            lines.append(f"- {tool['name']}(): {tool['description']}")
    return "\n".join(lines)


def get_tool_names() -> list:
    """Retourne la liste des noms d'outils"""
    return [t['name'] for t in TOOLS_DEFINITIONS]


__all__ = [
    'execute_tool',
    'register_tool', 
    'TOOLS_DEFINITIONS',
    'get_tools_description',
    'get_tool_names'
]
