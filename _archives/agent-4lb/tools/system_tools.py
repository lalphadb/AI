"""
🔧 Outils pour l'Agent 4LB
"""
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

def execute_command(command: str, timeout: int = 60, cwd: str = None) -> str:
    """Exécuter une commande shell."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        output = ""
        if result.stdout: output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr: output += f"STDERR:\n{result.stderr}\n"
        output += f"EXIT_CODE: {result.returncode}"
        return output
    except subprocess.TimeoutExpired:
        return f"ERREUR: Timeout après {timeout}s"
    except Exception as e:
        return f"ERREUR: {str(e)}"

def read_file(path: str) -> str:
    """Lire un fichier."""
    try:
        file_path = Path(path).expanduser().resolve()
        if not file_path.exists(): return f"ERREUR: Fichier non trouvé: {path}"
        content = file_path.read_text(encoding="utf-8")
        if len(content) > 50000: content = content[:50000] + "\n[... TRONQUÉ ...]"
        return f"Contenu de {path}:\n\n{content}"
    except Exception as e:
        return f"ERREUR: {str(e)}"

def write_file(path: str, content: str) -> str:
    """Écrire dans un fichier."""
    try:
        file_path = Path(path).expanduser().resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if file_path.exists():
            backup = f"{file_path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
            shutil.copy2(file_path, backup)
        file_path.write_text(content, encoding="utf-8")
        return f"✅ Fichier écrit: {path}"
    except Exception as e:
        return f"ERREUR: {str(e)}"

def list_directory(path: str, recursive: bool = False) -> str:
    """Lister un répertoire."""
    try:
        dir_path = Path(path).expanduser().resolve()
        if not dir_path.exists(): return f"ERREUR: Non trouvé: {path}"
        items = []
        if recursive:
            for item in sorted(dir_path.rglob("*"))[:200]:
                t = "📁" if item.is_dir() else "📄"
                items.append(f"{t} {item.relative_to(dir_path)}")
        else:
            for item in sorted(dir_path.iterdir())[:100]:
                t = "📁" if item.is_dir() else "📄"
                items.append(f"{t} {item.name}")
        return f"Contenu de {path}:\n" + "\n".join(items)
    except Exception as e:
        return f"ERREUR: {str(e)}"

def search_files(directory: str, pattern: str) -> str:
    """Rechercher des fichiers."""
    try:
        dir_path = Path(directory).expanduser().resolve()
        files = list(dir_path.rglob(pattern))[:100]
        if not files: return f"Aucun fichier pour '{pattern}'"
        return f"Fichiers trouvés:\n" + "\n".join([f"📄 {f}" for f in files])
    except Exception as e:
        return f"ERREUR: {str(e)}"

def docker_ps(all_containers: bool = False) -> str:
    """Lister les conteneurs Docker."""
    flag = "-a" if all_containers else ""
    return execute_command(f"docker ps {flag} --format 'table {{{{.Names}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}'")

def docker_logs(container: str, lines: int = 50) -> str:
    """Logs d'un conteneur."""
    return execute_command(f"docker logs --tail {lines} {container}")

def docker_restart(container: str) -> str:
    """Redémarrer un conteneur."""
    return execute_command(f"docker restart {container}")

def system_info() -> str:
    """Infos système."""
    info = []
    info.append(f"🖥️ Hostname: {execute_command('hostname').split('STDOUT:')[1].split('STDERR')[0].strip()}")
    info.append(f"🔧 CPU: {execute_command('nproc').split('STDOUT:')[1].split('STDERR')[0].strip()} cores")
    info.append(f"📊 Load: {execute_command('cat /proc/loadavg').split('STDOUT:')[1].split('STDERR')[0].strip()}")
    info.append(f"💾 RAM: {execute_command('free -h | grep Mem').split('STDOUT:')[1].split('STDERR')[0].strip()}")
    info.append(f"💿 Disk: {execute_command('df -h / | tail -1').split('STDOUT:')[1].split('STDERR')[0].strip()}")
    gpu = execute_command("nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 2>/dev/null || echo 'No GPU'")
    info.append(f"🎮 GPU: {gpu.split('STDOUT:')[1].split('STDERR')[0].strip()}")
    return "\n".join(info)

def service_status(service: str) -> str:
    """Statut d'un service."""
    return execute_command(f"systemctl status {service} --no-pager")

def git_status(path: str = None) -> str:
    """Statut Git."""
    cwd = path or "/home/lalpha/projets/infrastructure/4lb-docker-stack"
    return execute_command("git status", cwd=cwd)

def git_commit(message: str, path: str = None) -> str:
    """Commit Git."""
    cwd = path or "/home/lalpha/projets/infrastructure/4lb-docker-stack"
    execute_command("git add -A", cwd=cwd)
    return execute_command(f'git commit -m "{message}"', cwd=cwd)

def check_url(url: str) -> str:
    """Vérifier une URL."""
    return execute_command(f"curl -sI -o /dev/null -w 'HTTP %{{http_code}} - %{{time_total}}s' {url}")

def ollama_list() -> str:
    """Lister modèles Ollama."""
    return execute_command("ollama list")

def ollama_run(model: str, prompt: str) -> str:
    """Exécuter un prompt Ollama."""
    safe = prompt.replace('"', '\\"').replace("'", "\\'")
    return execute_command(f'ollama run {model} "{safe}"', timeout=120)

TOOLS = {
    "execute_command": execute_command, "read_file": read_file, "write_file": write_file,
    "list_directory": list_directory, "search_files": search_files, "docker_ps": docker_ps,
    "docker_logs": docker_logs, "docker_restart": docker_restart, "system_info": system_info,
    "service_status": service_status, "git_status": git_status, "git_commit": git_commit,
    "check_url": check_url, "ollama_list": ollama_list, "ollama_run": ollama_run,
}

def get_tools_description() -> str:
    """Description des outils."""
    return "\n".join([f"- {n}: {f.__doc__.split('.')[0] if f.__doc__ else 'N/A'}" for n, f in TOOLS.items()])
