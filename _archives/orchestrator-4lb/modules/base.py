"""
🔧 Module Base - Outils fondamentaux de l'Orchestrateur 4LB

Outils disponibles:
- read_file: Lire un fichier
- write_file: Écrire dans un fichier
- propose_diff: Proposer une modification (safe mode)
- run_command: Exécuter une commande shell
- list_directory: Lister un répertoire
- file_exists: Vérifier l'existence d'un fichier
- get_system_info: Informations système
- docker_status: État des conteneurs Docker
"""

import os
import subprocess
import json
import difflib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

from config.settings import PROTECTED_PATHS, ALLOWED_COMMANDS, LOGS_DIR

logger = logging.getLogger(__name__)


class BaseTools:
    """Outils de base pour la gestion du système"""
    
    def __init__(self):
        self.pending_diffs: Dict[str, str] = {}
        self.command_history: List[Dict] = []
    
    # === 1. READ FILE ===
    def read_file(self, path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """
        Lire le contenu d'un fichier
        
        Args:
            path: Chemin du fichier à lire
            encoding: Encodage du fichier (default: utf-8)
            
        Returns:
            Dict avec success, content ou error
        """
        try:
            file_path = Path(path).expanduser().resolve()
            
            if not file_path.exists():
                return {"success": False, "error": f"Fichier non trouvé: {path}"}
            
            if not file_path.is_file():
                return {"success": False, "error": f"N'est pas un fichier: {path}"}
            
            content = file_path.read_text(encoding=encoding)
            
            return {
                "success": True,
                "content": content,
                "path": str(file_path),
                "size": file_path.stat().st_size,
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            }
            
        except PermissionError:
            return {"success": False, "error": f"Permission refusée: {path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # === 2. WRITE FILE ===
    def write_file(self, path: str, content: str, backup: bool = True) -> Dict[str, Any]:
        """
        Écrire dans un fichier (avec backup automatique)
        
        Args:
            path: Chemin du fichier
            content: Contenu à écrire
            backup: Créer une sauvegarde si le fichier existe
            
        Returns:
            Dict avec success et info
        """
        try:
            file_path = Path(path).expanduser().resolve()
            
            # Vérifier si c'est un chemin protégé
            if self._is_protected(str(file_path)):
                return {
                    "success": False, 
                    "error": f"Chemin protégé! Utilisez propose_diff() pour: {path}"
                }
            
            # Backup si le fichier existe
            backup_path = None
            if backup and file_path.exists():
                backup_path = self._create_backup(file_path)
            
            # Créer le répertoire parent si nécessaire
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Écrire le fichier
            file_path.write_text(content, encoding="utf-8")
            
            logger.info(f"Fichier écrit: {file_path}")
            
            return {
                "success": True,
                "path": str(file_path),
                "size": len(content),
                "backup": backup_path
            }
            
        except Exception as e:
            logger.error(f"Erreur écriture {path}: {e}")
            return {"success": False, "error": str(e)}
    
    # === 3. PROPOSE DIFF ===
    def propose_diff(self, path: str, new_content: str) -> Dict[str, Any]:
        """
        Proposer une modification pour un fichier protégé
        
        Args:
            path: Chemin du fichier
            new_content: Nouveau contenu proposé
            
        Returns:
            Dict avec le diff et un ID de proposition
        """
        try:
            file_path = Path(path).expanduser().resolve()
            
            # Lire le contenu actuel
            if file_path.exists():
                current_content = file_path.read_text(encoding="utf-8")
            else:
                current_content = ""
            
            # Générer le diff
            diff = list(difflib.unified_diff(
                current_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                lineterm=""
            ))
            
            # Créer un ID unique pour cette proposition
            diff_id = f"diff_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_path.name}"
            
            # Stocker la proposition
            self.pending_diffs[diff_id] = {
                "path": str(file_path),
                "original": current_content,
                "proposed": new_content,
                "diff": "\n".join(diff),
                "created": datetime.now().isoformat()
            }
            
            return {
                "success": True,
                "diff_id": diff_id,
                "diff": "\n".join(diff),
                "lines_added": sum(1 for l in diff if l.startswith("+")),
                "lines_removed": sum(1 for l in diff if l.startswith("-")),
                "message": f"Proposition créée: {diff_id}. Utilisez apply_diff('{diff_id}') pour appliquer."
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def apply_diff(self, diff_id: str) -> Dict[str, Any]:
        """Appliquer une proposition de diff"""
        if diff_id not in self.pending_diffs:
            return {"success": False, "error": f"Diff non trouvé: {diff_id}"}
        
        diff_data = self.pending_diffs[diff_id]
        file_path = Path(diff_data["path"])
        
        # Créer un backup
        if file_path.exists():
            self._create_backup(file_path)
        
        # Appliquer les changements
        file_path.write_text(diff_data["proposed"], encoding="utf-8")
        
        # Supprimer la proposition
        del self.pending_diffs[diff_id]
        
        logger.info(f"Diff appliqué: {diff_id} -> {file_path}")
        
        return {
            "success": True,
            "path": str(file_path),
            "message": f"Modifications appliquées à {file_path}"
        }
    
    def list_pending_diffs(self) -> Dict[str, Any]:
        """Lister les diffs en attente"""
        return {
            "success": True,
            "count": len(self.pending_diffs),
            "diffs": [
                {"id": k, "path": v["path"], "created": v["created"]}
                for k, v in self.pending_diffs.items()
            ]
        }
    
    # === 4. RUN COMMAND ===
    def run_command(self, command: str, timeout: int = 60, cwd: Optional[str] = None) -> Dict[str, Any]:
        """
        Exécuter une commande shell
        
        Args:
            command: Commande à exécuter
            timeout: Timeout en secondes
            cwd: Répertoire de travail
            
        Returns:
            Dict avec stdout, stderr, returncode
        """
        try:
            # Vérifier si la commande est autorisée
            cmd_parts = command.split()
            if cmd_parts and not self._is_command_allowed(cmd_parts[0]):
                return {
                    "success": False,
                    "error": f"Commande non autorisée: {cmd_parts[0]}",
                    "allowed": ALLOWED_COMMANDS
                }
            
            # Exécuter la commande
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )
            
            # Logger l'exécution
            self.command_history.append({
                "command": command,
                "returncode": result.returncode,
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": command
            }
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Timeout après {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # === 5. LIST DIRECTORY ===
    def list_directory(self, path: str, recursive: bool = False, pattern: str = "*") -> Dict[str, Any]:
        """
        Lister le contenu d'un répertoire
        
        Args:
            path: Chemin du répertoire
            recursive: Lister récursivement
            pattern: Pattern glob pour filtrer
            
        Returns:
            Dict avec la liste des fichiers/dossiers
        """
        try:
            dir_path = Path(path).expanduser().resolve()
            
            if not dir_path.exists():
                return {"success": False, "error": f"Répertoire non trouvé: {path}"}
            
            if not dir_path.is_dir():
                return {"success": False, "error": f"N'est pas un répertoire: {path}"}
            
            if recursive:
                items = list(dir_path.rglob(pattern))
            else:
                items = list(dir_path.glob(pattern))
            
            files = []
            directories = []
            
            for item in items[:500]:  # Limiter à 500 items
                info = {
                    "name": item.name,
                    "path": str(item),
                    "relative": str(item.relative_to(dir_path)) if item != dir_path else "."
                }
                
                if item.is_file():
                    info["size"] = item.stat().st_size
                    info["type"] = "file"
                    files.append(info)
                elif item.is_dir():
                    info["type"] = "directory"
                    directories.append(info)
            
            return {
                "success": True,
                "path": str(dir_path),
                "directories": directories,
                "files": files,
                "total_dirs": len(directories),
                "total_files": len(files)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # === 6. FILE EXISTS ===
    def file_exists(self, path: str) -> Dict[str, Any]:
        """Vérifier si un fichier/dossier existe"""
        try:
            file_path = Path(path).expanduser().resolve()
            exists = file_path.exists()
            
            result = {
                "success": True,
                "exists": exists,
                "path": str(file_path)
            }
            
            if exists:
                stat = file_path.stat()
                result["is_file"] = file_path.is_file()
                result["is_dir"] = file_path.is_dir()
                result["size"] = stat.st_size if file_path.is_file() else None
                result["modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # === 7. GET SYSTEM INFO ===
    def get_system_info(self) -> Dict[str, Any]:
        """Obtenir les informations système"""
        try:
            info = {}
            
            # CPU
            cpu_result = self.run_command("nproc")
            if cpu_result["success"]:
                info["cpu_cores"] = int(cpu_result["stdout"].strip())
            
            # Mémoire
            mem_result = self.run_command("free -h")
            if mem_result["success"]:
                info["memory"] = mem_result["stdout"]
            
            # Disque
            disk_result = self.run_command("df -h /")
            if disk_result["success"]:
                info["disk"] = disk_result["stdout"]
            
            # Uptime
            uptime_result = self.run_command("uptime")
            if uptime_result["success"]:
                info["uptime"] = uptime_result["stdout"].strip()
            
            # GPU (si disponible)
            gpu_result = self.run_command("nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader 2>/dev/null || echo 'No GPU'")
            if gpu_result["success"]:
                info["gpu"] = gpu_result["stdout"].strip()
            
            # Hostname
            hostname_result = self.run_command("hostname")
            if hostname_result["success"]:
                info["hostname"] = hostname_result["stdout"].strip()
            
            return {"success": True, "info": info}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # === 8. DOCKER STATUS ===
    def docker_status(self, all_containers: bool = False) -> Dict[str, Any]:
        """
        Obtenir le statut des conteneurs Docker
        
        Args:
            all_containers: Inclure les conteneurs arrêtés
            
        Returns:
            Dict avec la liste des conteneurs
        """
        try:
            flag = "-a" if all_containers else ""
            result = self.run_command(
                f"docker ps {flag} --format '{{{{json .}}}}'"
            )
            
            if not result["success"]:
                return result
            
            containers = []
            for line in result["stdout"].strip().split("\n"):
                if line:
                    try:
                        containers.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            
            # Stats globales
            stats_result = self.run_command("docker system df --format '{{json .}}'")
            
            return {
                "success": True,
                "containers": containers,
                "count": len(containers),
                "running": sum(1 for c in containers if c.get("State") == "running"),
                "system_df": stats_result.get("stdout", "")
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # === Méthodes utilitaires privées ===
    
    def _is_protected(self, path: str) -> bool:
        """Vérifier si un chemin est protégé"""
        path = str(Path(path).resolve())
        for protected in PROTECTED_PATHS:
            if path.startswith(protected) or path == protected:
                return True
        return False
    
    def _is_command_allowed(self, cmd: str) -> bool:
        """Vérifier si une commande est autorisée"""
        cmd = cmd.split("/")[-1]  # Extraire le nom de la commande
        return any(cmd.startswith(allowed.split()[0]) for allowed in ALLOWED_COMMANDS)
    
    def _create_backup(self, file_path: Path) -> str:
        """Créer une sauvegarde d'un fichier"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}.{timestamp}.bak"
        backup_path = LOGS_DIR / "file_backups" / backup_name
        
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        import shutil
        shutil.copy2(file_path, backup_path)
        
        return str(backup_path)


# Instance singleton
base_tools = BaseTools()
