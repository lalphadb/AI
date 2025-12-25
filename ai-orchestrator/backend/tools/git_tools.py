"""
Outils Git pour AI Orchestrator v4.0
- git_status
- git_diff
- git_log
- git_pull
"""

from tools import register_tool
from utils.async_subprocess import run_command_async


@register_tool("git_status")
async def git_status(params: dict) -> str:
    """Obtenir le statut d'un dépôt Git"""
    path = params.get("path", ".")
    
    output, code = await run_command_async(
        f"cd {path} && git status",
        timeout=15
    )
    
    if code != 0:
        return f"❌ Erreur Git ou pas un dépôt: {path}"
    
    return f"Git status ({path}):\n{output}"


@register_tool("git_diff")
async def git_diff(params: dict) -> str:
    """Voir les différences non commitées"""
    path = params.get("path", ".")
    file_path = params.get("file", "")
    
    cmd = f"cd {path} && git diff"
    if file_path:
        cmd += f" -- {file_path}"
    
    output, code = await run_command_async(cmd, timeout=30)
    
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
    
    output, code = await run_command_async(
        f"cd {path} && git log --oneline -n {count}",
        timeout=15
    )
    
    return f"Git log ({path}, {count} derniers commits):\n{output}"


@register_tool("git_pull")
async def git_pull(params: dict) -> str:
    """Pull les dernières modifications"""
    path = params.get("path", ".")
    
    output, code = await run_command_async(
        f"cd {path} && git pull",
        timeout=60
    )
    
    status = "✅" if code == 0 else "❌"
    return f"{status} Git pull ({path}):\n{output}"


@register_tool("git_branch")
async def git_branch(params: dict) -> str:
    """Lister les branches Git"""
    path = params.get("path", ".")
    
    output, code = await run_command_async(
        f"cd {path} && git branch -a",
        timeout=15
    )
    
    return f"Branches Git ({path}):\n{output}"
