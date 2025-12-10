"""
🔧 Modules Orchestrateur 4LB

Modules disponibles:
- base: Outils fondamentaux (8 outils)
- gitops: Gestion versionnée (6 outils)
- backup: Sauvegarde automatisée (5 outils)
- self_improve: Auto-amélioration IA (3 outils)

Total: 22 outils
"""

from .base import base_tools, BaseTools
from .gitops import gitops_tools, GitOpsTools
from .backup import backup_tools, BackupTools
from .self_improve import self_improve_tools, SelfImproveTools

__all__ = [
    "base_tools",
    "gitops_tools", 
    "backup_tools",
    "self_improve_tools",
    "BaseTools",
    "GitOpsTools",
    "BackupTools",
    "SelfImproveTools"
]

# Catalogue des outils
TOOLS_CATALOG = {
    "base": {
        "description": "Outils fondamentaux",
        "tools": [
            "read_file",
            "write_file", 
            "propose_diff",
            "apply_diff",
            "run_command",
            "list_directory",
            "file_exists",
            "get_system_info",
            "docker_status"
        ]
    },
    "gitops": {
        "description": "Gestion versionnée GitOps",
        "tools": [
            "gitops_init",
            "gitops_status",
            "gitops_commit",
            "gitops_rollback",
            "gitops_setup_hooks",
            "gitops_log"
        ]
    },
    "backup": {
        "description": "Sauvegarde automatisée",
        "tools": [
            "backup_postgres",
            "backup_configs",
            "backup_ollama_models",
            "backup_full",
            "backup_s3"
        ]
    },
    "self_improve": {
        "description": "Auto-amélioration avec IA",
        "tools": [
            "self_improve_analyze_logs",
            "self_improve_anomalies",
            "self_improve_suggestions"
        ]
    }
}

def get_all_tools():
    """Retourne tous les outils disponibles"""
    return {
        "base": base_tools,
        "gitops": gitops_tools,
        "backup": backup_tools,
        "self_improve": self_improve_tools
    }

def get_tool_count():
    """Compte le nombre total d'outils"""
    total = 0
    for module in TOOLS_CATALOG.values():
        total += len(module["tools"])
    return total
