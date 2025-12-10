"""
💾 Module Backup - Sauvegarde automatisée

Outils disponibles:
- backup_postgres: Sauvegarde PostgreSQL
- backup_configs: Sauvegarde des configurations
- backup_ollama_models: Liste des modèles Ollama
- backup_full: Sauvegarde complète
- backup_s3: Upload vers S3/MinIO
"""

import os
import subprocess
import tarfile
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging
import shutil

from config.settings import (
    BACKUPS_DIR, INFRA_DIR, PROJECTS_DIR,
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DATABASES,
    S3_ENABLED, S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY
)

logger = logging.getLogger(__name__)


class BackupTools:
    """Outils de sauvegarde"""
    
    def __init__(self):
        self.backup_dir = BACKUPS_DIR
        self.backup_dir.mkdir(exist_ok=True)
    
    def _get_timestamp(self) -> str:
        """Générer un timestamp pour les noms de fichiers"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # === 1. BACKUP POSTGRES ===
    def backup_postgres(
        self, 
        databases: Optional[List[str]] = None,
        compress: bool = True
    ) -> Dict[str, Any]:
        """
        Sauvegarder les bases de données PostgreSQL
        
        Args:
            databases: Liste des bases à sauvegarder (default: toutes)
            compress: Compresser le dump
            
        Returns:
            Dict avec les chemins des sauvegardes
        """
        try:
            databases = databases or POSTGRES_DATABASES
            timestamp = self._get_timestamp()
            backup_subdir = self.backup_dir / "postgres" / timestamp
            backup_subdir.mkdir(parents=True, exist_ok=True)
            
            backups = []
            errors = []
            
            for db in databases:
                dump_file = backup_subdir / f"{db}.sql"
                
                # Construire la commande pg_dump
                env = os.environ.copy()
                if POSTGRES_PASSWORD:
                    env["PGPASSWORD"] = POSTGRES_PASSWORD
                
                cmd = [
                    "pg_dump",
                    "-h", POSTGRES_HOST,
                    "-p", str(POSTGRES_PORT),
                    "-U", POSTGRES_USER,
                    "-d", db,
                    "-f", str(dump_file)
                ]
                
                # Alternative: via Docker si pg_dump local non disponible
                docker_cmd = f"docker exec postgres pg_dump -U {POSTGRES_USER} {db}"
                
                try:
                    # Essayer d'abord pg_dump direct
                    result = subprocess.run(
                        cmd,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    
                    if result.returncode != 0:
                        # Fallback Docker
                        result = subprocess.run(
                            docker_cmd,
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=300
                        )
                        
                        if result.returncode == 0:
                            dump_file.write_text(result.stdout)
                    
                    if result.returncode == 0 and dump_file.exists():
                        # Compresser si demandé
                        if compress:
                            import gzip
                            with open(dump_file, 'rb') as f_in:
                                with gzip.open(f"{dump_file}.gz", 'wb') as f_out:
                                    shutil.copyfileobj(f_in, f_out)
                            dump_file.unlink()  # Supprimer l'original
                            dump_file = Path(f"{dump_file}.gz")
                        
                        backups.append({
                            "database": db,
                            "path": str(dump_file),
                            "size": dump_file.stat().st_size
                        })
                    else:
                        errors.append({
                            "database": db,
                            "error": result.stderr or "Échec du dump"
                        })
                        
                except Exception as e:
                    errors.append({"database": db, "error": str(e)})
            
            logger.info(f"Backup PostgreSQL: {len(backups)} succès, {len(errors)} erreurs")
            
            return {
                "success": len(backups) > 0,
                "backups": backups,
                "errors": errors,
                "timestamp": timestamp,
                "backup_dir": str(backup_subdir)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # === 2. BACKUP CONFIGS ===
    def backup_configs(self, include_secrets: bool = False) -> Dict[str, Any]:
        """
        Sauvegarder les fichiers de configuration
        
        Args:
            include_secrets: Inclure les fichiers .env
            
        Returns:
            Dict avec le chemin de l'archive
        """
        try:
            timestamp = self._get_timestamp()
            archive_name = f"configs_{timestamp}.tar.gz"
            archive_path = self.backup_dir / "configs" / archive_name
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            
            configs_to_backup = []
            
            # Configurations Docker/Infrastructure
            if INFRA_DIR.exists():
                for pattern in ["*.yml", "*.yaml", "*.json", "*.conf", "*.toml"]:
                    configs_to_backup.extend(INFRA_DIR.rglob(pattern))
                
                # Inclure .env si demandé
                if include_secrets:
                    configs_to_backup.extend(INFRA_DIR.rglob("*.env"))
                    configs_to_backup.extend(INFRA_DIR.rglob(".env*"))
            
            # Filtrer les fichiers existants
            configs_to_backup = [f for f in configs_to_backup if f.is_file()]
            
            # Exclure certains patterns
            exclude_patterns = ["node_modules", ".git", "__pycache__", "venv"]
            configs_to_backup = [
                f for f in configs_to_backup 
                if not any(p in str(f) for p in exclude_patterns)
            ]
            
            # Créer l'archive
            with tarfile.open(archive_path, "w:gz") as tar:
                for config_file in configs_to_backup:
                    try:
                        arcname = str(config_file.relative_to(INFRA_DIR.parent))
                        tar.add(config_file, arcname=arcname)
                    except Exception as e:
                        logger.warning(f"Impossible d'ajouter {config_file}: {e}")
            
            logger.info(f"Backup configs: {len(configs_to_backup)} fichiers")
            
            return {
                "success": True,
                "archive": str(archive_path),
                "files_count": len(configs_to_backup),
                "size": archive_path.stat().st_size,
                "timestamp": timestamp
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # === 3. BACKUP OLLAMA MODELS ===
    def backup_ollama_models(self) -> Dict[str, Any]:
        """
        Sauvegarder la liste des modèles Ollama installés
        (pas les modèles eux-mêmes, juste la liste pour restauration)
        
        Returns:
            Dict avec la liste des modèles
        """
        try:
            timestamp = self._get_timestamp()
            
            # Lister les modèles
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            models = []
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")[1:]  # Skip header
                for line in lines:
                    parts = line.split()
                    if parts:
                        models.append({
                            "name": parts[0],
                            "size": parts[1] if len(parts) > 1 else "unknown",
                            "modified": " ".join(parts[2:]) if len(parts) > 2 else "unknown"
                        })
            
            # Sauvegarder dans un fichier JSON
            backup_file = self.backup_dir / "ollama" / f"models_{timestamp}.json"
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            
            backup_data = {
                "timestamp": timestamp,
                "models": models,
                "restore_commands": [f"ollama pull {m['name']}" for m in models]
            }
            
            backup_file.write_text(json.dumps(backup_data, indent=2))
            
            logger.info(f"Backup Ollama: {len(models)} modèles listés")
            
            return {
                "success": True,
                "models": models,
                "count": len(models),
                "backup_file": str(backup_file),
                "restore_script": "\n".join(backup_data["restore_commands"])
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # === 4. BACKUP FULL ===
    def backup_full(self, include_secrets: bool = False) -> Dict[str, Any]:
        """
        Effectuer une sauvegarde complète
        
        Args:
            include_secrets: Inclure les secrets
            
        Returns:
            Dict avec le résumé de toutes les sauvegardes
        """
        try:
            timestamp = self._get_timestamp()
            results = {
                "timestamp": timestamp,
                "postgres": None,
                "configs": None,
                "ollama": None,
                "success": True
            }
            
            # PostgreSQL
            logger.info("Backup PostgreSQL...")
            results["postgres"] = self.backup_postgres()
            
            # Configs
            logger.info("Backup Configs...")
            results["configs"] = self.backup_configs(include_secrets=include_secrets)
            
            # Ollama
            logger.info("Backup Ollama models list...")
            results["ollama"] = self.backup_ollama_models()
            
            # Résumé
            success_count = sum(1 for k in ["postgres", "configs", "ollama"] 
                               if results[k] and results[k].get("success"))
            
            results["summary"] = {
                "total_backups": 3,
                "successful": success_count,
                "backup_dir": str(self.backup_dir)
            }
            
            results["success"] = success_count == 3
            
            logger.info(f"Backup complet: {success_count}/3 succès")
            
            return results
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # === 5. BACKUP S3 ===
    def backup_s3(self, local_path: str, remote_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload une sauvegarde vers S3/MinIO
        
        Args:
            local_path: Chemin du fichier local
            remote_path: Chemin distant (optionnel)
            
        Returns:
            Dict avec le statut de l'upload
        """
        if not S3_ENABLED:
            return {
                "success": False,
                "error": "S3 non configuré. Définissez S3_ENABLED=true et les credentials."
            }
        
        try:
            local_file = Path(local_path)
            
            if not local_file.exists():
                return {"success": False, "error": f"Fichier non trouvé: {local_path}"}
            
            # Construire le chemin distant
            if not remote_path:
                remote_path = f"backups/{datetime.now().strftime('%Y/%m/%d')}/{local_file.name}"
            
            # Utiliser AWS CLI ou boto3
            # Option 1: AWS CLI
            env = os.environ.copy()
            env["AWS_ACCESS_KEY_ID"] = S3_ACCESS_KEY
            env["AWS_SECRET_ACCESS_KEY"] = S3_SECRET_KEY
            
            cmd = [
                "aws", "s3", "cp",
                str(local_file),
                f"s3://{S3_BUCKET}/{remote_path}",
                "--endpoint-url", S3_ENDPOINT
            ]
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                logger.info(f"Upload S3 réussi: {remote_path}")
                return {
                    "success": True,
                    "local_path": str(local_file),
                    "remote_path": f"s3://{S3_BUCKET}/{remote_path}",
                    "size": local_file.stat().st_size
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr or "Échec de l'upload"
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # === Méthodes utilitaires ===
    
    def list_backups(self, backup_type: Optional[str] = None) -> Dict[str, Any]:
        """Lister les sauvegardes existantes"""
        try:
            backups = {}
            
            for subdir in self.backup_dir.iterdir():
                if subdir.is_dir() and (not backup_type or subdir.name == backup_type):
                    files = list(subdir.rglob("*"))
                    files = [f for f in files if f.is_file()]
                    
                    backups[subdir.name] = [
                        {
                            "name": f.name,
                            "path": str(f),
                            "size": f.stat().st_size,
                            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                        }
                        for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:20]
                    ]
            
            return {
                "success": True,
                "backups": backups,
                "backup_dir": str(self.backup_dir)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def cleanup_old_backups(self, days: int = 30) -> Dict[str, Any]:
        """Supprimer les sauvegardes de plus de X jours"""
        try:
            from datetime import timedelta
            
            cutoff = datetime.now() - timedelta(days=days)
            deleted = []
            
            for backup_file in self.backup_dir.rglob("*"):
                if backup_file.is_file():
                    mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if mtime < cutoff:
                        backup_file.unlink()
                        deleted.append(str(backup_file))
            
            # Supprimer les dossiers vides
            for subdir in self.backup_dir.rglob("*"):
                if subdir.is_dir() and not any(subdir.iterdir()):
                    subdir.rmdir()
            
            logger.info(f"Nettoyage backups: {len(deleted)} fichiers supprimés")
            
            return {
                "success": True,
                "deleted_count": len(deleted),
                "deleted_files": deleted[:50],  # Limiter la liste
                "cutoff_date": cutoff.isoformat()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# Instance singleton
backup_tools = BackupTools()
