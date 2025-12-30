"""
Outils Git pour AI Orchestrator v4.0
- git_status
- git_diff
- git_log
- git_pull
Version SÉCURISÉE: Utilise cwd au lieu de 'cd &&'
"""

from tools import register_tool
from utils.async_subprocess import run_command_async


@register_tool("git_status")
async def git_status(params: dict, security_validator=None, audit_logger=None) -> str:
    """Obtenir le statut d'un dépôt Git"""
    path = params.get("path", ".")

    # Validation du chemin si nécessaire
    if security_validator:
        allowed, reason = security_validator(f"read {path}")  # Simulation check
        if not allowed:
            return f"🚫 Accès refusé au repo: {reason}"

    # Utilisation de cwd pour changer de dossier, et liste pour la commande
    cmd = ["git", "status"]
    output, code = await run_command_async(cmd, cwd=path, timeout=15)

    if code != 0:
        return f"❌ Erreur Git ou pas un dépôt: {path}\n{output}"

    return f"Git status ({path}):\n{output}"


@register_tool("git_diff")
async def git_diff(params: dict) -> str:
    """Voir les différences non commitées"""
    path = params.get("path", ".")
    file_path = params.get("file", "")

    cmd = ["git", "diff"]
    if file_path:
        cmd.extend(["--", file_path])

    output, code = await run_command_async(cmd, cwd=path, timeout=30)

    if not output.strip():
        return "Aucune modification non commitée"

    return f"Git diff ({path}):\n{output[:5000]}"


@register_tool("git_log")
async def git_log(params: dict) -> str:
    """Historique des commits Git"""
    path = params.get("path", ".")
    count = params.get("count", 10)

    try:
        count = min(int(count), 50)
    except (ValueError, TypeError):
        count = 10

    cmd = ["git", "log", "--oneline", "-n", str(count)]
    output, code = await run_command_async(cmd, cwd=path, timeout=15)

    return f"Git log ({path}, {count} derniers commits):\n{output}"


@register_tool("git_pull")
async def git_pull(params: dict) -> str:
    """Pull les dernières modifications"""
    path = params.get("path", ".")

    cmd = ["git", "pull"]
    output, code = await run_command_async(cmd, cwd=path, timeout=60)

    status = "✅" if code == 0 else "❌"
    return f"{status} Git pull ({path}):\n{output}"


@register_tool("git_branch")
async def git_branch(params: dict) -> str:
    """Lister les branches Git"""
    path = params.get("path", ".")

    cmd = ["git", "branch", "-a"]
    output, code = await run_command_async(cmd, cwd=path, timeout=15)

    return f"Branches Git ({path}):\n{output}"
