"""
🐳 Outils Docker - LangChain Tools
"""
from .system import execute_command

DOCKER_STACK_PATH = "/home/lalpha/projets/infrastructure/4lb-docker-stack"


def docker_ps(all_containers: bool = False) -> str:
    """Lister les conteneurs Docker actifs (ou tous)."""
    flag = "-a" if all_containers else ""
    return execute_command(
        f"docker ps {flag} --format 'table {{{{.Names}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}\\t{{{{.Image}}}}'"
    )


def docker_logs(container: str, lines: int = 50, follow: bool = False) -> str:
    """Afficher les logs d'un conteneur Docker."""
    follow_flag = "-f" if follow else ""
    return execute_command(f"docker logs --tail {lines} {follow_flag} {container}", timeout=10)


def docker_restart(container: str) -> str:
    """Redémarrer un conteneur Docker."""
    return execute_command(f"docker restart {container}")


def docker_stop(container: str) -> str:
    """Arrêter un conteneur Docker."""
    return execute_command(f"docker stop {container}")


def docker_start(container: str) -> str:
    """Démarrer un conteneur Docker."""
    return execute_command(f"docker start {container}")


def docker_compose_up(path: str = None, detach: bool = True) -> str:
    """Lancer docker compose up."""
    stack_path = path or DOCKER_STACK_PATH
    flag = "-d" if detach else ""
    return execute_command(f"docker compose up {flag}", cwd=stack_path)


def docker_compose_down(path: str = None) -> str:
    """Arrêter docker compose."""
    stack_path = path or DOCKER_STACK_PATH
    return execute_command("docker compose down", cwd=stack_path)


def docker_stats(container: str = None) -> str:
    """Afficher les statistiques Docker."""
    if container:
        return execute_command(f"docker stats --no-stream {container}")
    return execute_command("docker stats --no-stream")


def docker_inspect(container: str) -> str:
    """Inspecter un conteneur Docker."""
    return execute_command(f"docker inspect {container}")


def docker_network_ls() -> str:
    """Lister les réseaux Docker."""
    return execute_command("docker network ls")


def docker_volume_ls() -> str:
    """Lister les volumes Docker."""
    return execute_command("docker volume ls")


def docker_prune() -> str:
    """Nettoyer les ressources Docker inutilisées."""
    return execute_command("docker system prune -f")
