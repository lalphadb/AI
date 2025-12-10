"""
🖥️ Outils Système - LangChain Tools
"""
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional


def execute_command(command: str, timeout: int = 60, cwd: str = None) -> str:
    """Exécuter une commande shell sur le serveur."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout, 
            cwd=cwd
        )
        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        output += f"EXIT_CODE: {result.returncode}"
        return output
    except subprocess.TimeoutExpired:
        return f"ERREUR: Timeout après {timeout}s"
    except Exception as e:
        return f"ERREUR: {str(e)}"


def read_file(path: str, max_lines: int = 500) -> str:
    """Lire le contenu d'un fichier."""
    try:
        file_path = Path(path).expanduser().resolve()
        if not file_path.exists():
            return f"ERREUR: Fichier non trouvé: {path}"
        if not file_path.is_file():
            return f"ERREUR: Ce n'est pas un fichier: {path}"
        
        content = file_path.read_text(encoding="utf-8", errors="replace")
        lines = content.split('\n')
        
        if len(lines) > max_lines:
            content = '\n'.join(lines[:max_lines])
            content += f"\n\n[... TRONQUÉ - {len(lines)} lignes au total ...]"
        
        return f"Contenu de {path}:\n\n{content}"
    except Exception as e:
        return f"ERREUR: {str(e)}"


def write_file(path: str, content: str, backup: bool = True) -> str:
    """Écrire du contenu dans un fichier."""
    try:
        file_path = Path(path).expanduser().resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Backup si fichier existant
        if backup and file_path.exists():
            backup_path = f"{file_path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
            shutil.copy2(file_path, backup_path)
        
        file_path.write_text(content, encoding="utf-8")
        return f"✅ Fichier écrit avec succès: {path}"
    except Exception as e:
        return f"ERREUR: {str(e)}"


def list_directory(path: str, recursive: bool = False, max_items: int = 200) -> str:
    """Lister le contenu d'un répertoire."""
    try:
        dir_path = Path(path).expanduser().resolve()
        if not dir_path.exists():
            return f"ERREUR: Répertoire non trouvé: {path}"
        if not dir_path.is_dir():
            return f"ERREUR: Ce n'est pas un répertoire: {path}"
        
        items = []
        if recursive:
            for item in sorted(dir_path.rglob("*"))[:max_items]:
                icon = "📁" if item.is_dir() else "📄"
                items.append(f"{icon} {item.relative_to(dir_path)}")
        else:
            for item in sorted(dir_path.iterdir())[:max_items]:
                icon = "📁" if item.is_dir() else "📄"
                size = ""
                if item.is_file():
                    size = f" ({item.stat().st_size} bytes)"
                items.append(f"{icon} {item.name}{size}")
        
        return f"Contenu de {path}:\n" + "\n".join(items)
    except Exception as e:
        return f"ERREUR: {str(e)}"


def search_files(directory: str, pattern: str, max_results: int = 100) -> str:
    """Rechercher des fichiers par pattern (glob)."""
    try:
        dir_path = Path(directory).expanduser().resolve()
        if not dir_path.exists():
            return f"ERREUR: Répertoire non trouvé: {directory}"
        
        files = list(dir_path.rglob(pattern))[:max_results]
        
        if not files:
            return f"Aucun fichier trouvé pour '{pattern}' dans {directory}"
        
        result = f"Fichiers trouvés ({len(files)}):\n"
        result += "\n".join([f"📄 {f}" for f in files])
        return result
    except Exception as e:
        return f"ERREUR: {str(e)}"


def system_info() -> str:
    """Obtenir les informations système (CPU, RAM, disque, GPU)."""
    info = []
    
    try:
        # Hostname
        result = execute_command("hostname")
        hostname = result.split("STDOUT:")[1].split("STDERR")[0].strip() if "STDOUT:" in result else "inconnu"
        info.append(f"🖥️ Hostname: {hostname}")
        
        # CPU
        result = execute_command("nproc")
        cpus = result.split("STDOUT:")[1].split("STDERR")[0].strip() if "STDOUT:" in result else "?"
        info.append(f"🔧 CPU: {cpus} cores")
        
        # Load
        result = execute_command("cat /proc/loadavg")
        load = result.split("STDOUT:")[1].split("STDERR")[0].strip() if "STDOUT:" in result else "?"
        info.append(f"📊 Load: {load}")
        
        # RAM
        result = execute_command("free -h | grep Mem")
        ram = result.split("STDOUT:")[1].split("STDERR")[0].strip() if "STDOUT:" in result else "?"
        info.append(f"💾 RAM: {ram}")
        
        # Disk
        result = execute_command("df -h / | tail -1")
        disk = result.split("STDOUT:")[1].split("STDERR")[0].strip() if "STDOUT:" in result else "?"
        info.append(f"💿 Disk: {disk}")
        
        # GPU
        result = execute_command("nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 2>/dev/null || echo 'No GPU'")
        gpu = result.split("STDOUT:")[1].split("STDERR")[0].strip() if "STDOUT:" in result else "No GPU"
        info.append(f"🎮 GPU: {gpu}")
        
        # Uptime
        result = execute_command("uptime -p")
        uptime = result.split("STDOUT:")[1].split("STDERR")[0].strip() if "STDOUT:" in result else "?"
        info.append(f"⏱️ Uptime: {uptime}")
        
    except Exception as e:
        info.append(f"ERREUR: {str(e)}")
    
    return "\n".join(info)
