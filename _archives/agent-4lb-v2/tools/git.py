"""
📦 Outils Git - LangChain Tools
"""
from .system import execute_command

DEFAULT_REPO = "/home/lalpha/projets/infrastructure/4lb-docker-stack"


def git_status(path: str = None) -> str:
    """Afficher le statut Git d'un dépôt."""
    repo = path or DEFAULT_REPO
    return execute_command("git status", cwd=repo)


def git_diff(path: str = None, staged: bool = False) -> str:
    """Afficher les différences Git."""
    repo = path or DEFAULT_REPO
    flag = "--staged" if staged else ""
    return execute_command(f"git diff {flag}", cwd=repo)


def git_log(path: str = None, count: int = 10) -> str:
    """Afficher l'historique Git."""
    repo = path or DEFAULT_REPO
    return execute_command(f"git log --oneline -n {count}", cwd=repo)


def git_commit(message: str, path: str = None) -> str:
    """Créer un commit Git."""
    repo = path or DEFAULT_REPO
    # Add all changes
    execute_command("git add -A", cwd=repo)
    return execute_command(f'git commit -m "{message}"', cwd=repo)


def git_pull(path: str = None) -> str:
    """Tirer les changements du remote."""
    repo = path or DEFAULT_REPO
    return execute_command("git pull", cwd=repo)


def git_push(path: str = None) -> str:
    """Pousser les changements vers le remote."""
    repo = path or DEFAULT_REPO
    return execute_command("git push", cwd=repo)


def git_branch(path: str = None) -> str:
    """Lister les branches Git."""
    repo = path or DEFAULT_REPO
    return execute_command("git branch -a", cwd=repo)


def git_checkout(branch: str, path: str = None) -> str:
    """Changer de branche Git."""
    repo = path or DEFAULT_REPO
    return execute_command(f"git checkout {branch}", cwd=repo)


def git_stash(path: str = None, pop: bool = False) -> str:
    """Gérer le stash Git."""
    repo = path or DEFAULT_REPO
    cmd = "git stash pop" if pop else "git stash"
    return execute_command(cmd, cwd=repo)
