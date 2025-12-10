"""
🔧 LangChain Tools - Agent 4LB v2
"""
from .system import (
    execute_command,
    read_file,
    write_file,
    list_directory,
    search_files,
    system_info
)
from .docker import (
    docker_ps,
    docker_logs,
    docker_restart,
    docker_compose_up,
    docker_compose_down
)
from .git import git_status, git_commit, git_pull, git_push
from .network import check_url, get_ssl_info
from .llm import ollama_list, ollama_run, ollama_pull

# Tous les outils disponibles
ALL_TOOLS = {
    # System
    "execute_command": execute_command,
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
    "search_files": search_files,
    "system_info": system_info,
    # Docker
    "docker_ps": docker_ps,
    "docker_logs": docker_logs,
    "docker_restart": docker_restart,
    "docker_compose_up": docker_compose_up,
    "docker_compose_down": docker_compose_down,
    # Git
    "git_status": git_status,
    "git_commit": git_commit,
    "git_pull": git_pull,
    "git_push": git_push,
    # Network
    "check_url": check_url,
    "get_ssl_info": get_ssl_info,
    # LLM
    "ollama_list": ollama_list,
    "ollama_run": ollama_run,
    "ollama_pull": ollama_pull,
}

__all__ = ["ALL_TOOLS"]
