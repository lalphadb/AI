#!/usr/bin/env python3
"""
💾 Backup System v2.0
Sauvegarde automatique vers Cloudflare R2
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Charger .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

# Configuration S3/R2
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
S3_BUCKET = os.getenv("S3_BUCKET", "ai4lb-backups")
S3_REGION = os.getenv("S3_REGION", "auto")

BACKUP_DIR = Path("/home/lalpha/projets/ai-tools/backup-system/local")
BACKUP_DIR.mkdir(exist_ok=True)

# Éléments à sauvegarder
BACKUP_TARGETS = {
    "docker-compose": {
        "type": "directory",
        "path": "/home/lalpha/projets/infrastructure/4lb-docker-stack",
        "exclude": [".git", "node_modules", "__pycache__", "*.log"]
    },
    "ai-orchestrator": {
        "type": "directory", 
        "path": "/home/lalpha/projets/ai-tools/ai-orchestrator",
        "exclude": ["node_modules", "__pycache__", ".git", "*.log"]
    },
    "mcp-servers": {
        "type": "directory",
        "path": "/home/lalpha/projets/ai-tools/mcp-servers",
        "exclude": ["node_modules", "__pycache__", ".git"]
    },
    "documentation": {
        "type": "directory",
        "path": "/home/lalpha/documentation",
        "exclude": []
    },
    "scripts": {
        "type": "directory",
        "path": "/home/lalpha/scripts",
        "exclude": ["*.log"]
    },
    "postgres": {
        "type": "database",
        "container": "postgres",
        "database": "all"
    },
    "self-improvement-reports": {
        "type": "directory",
        "path": "/home/lalpha/projets/ai-tools/self-improvement/reports",
        "exclude": []
    }
}


def run_command(cmd: List[str], capture: bool = True) -> tuple:
    """Exécute une commande shell"""
    try:
        result = subprocess.run(cmd, capture_output=capture, text=True, timeout=600)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"
    except Exception as e:
        return False, "", str(e)


def backup_directory(name: str, config: Dict) -> Optional[Path]:
    """Sauvegarde un répertoire en tar.gz"""
    source = Path(config["path"])
    if not source.exists():
        print(f"   ⚠️ Répertoire non trouvé: {source}")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"{name}_{timestamp}.tar.gz"
    
    excludes = config.get("exclude", [])
    exclude_args = []
    for exc in excludes:
        exclude_args.extend(["--exclude", exc])
    
    cmd = ["tar", "-czf", str(backup_file)] + exclude_args + ["-C", str(source.parent), source.name]
    success, stdout, stderr = run_command(cmd)
    
    if success:
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        print(f"   ✅ {name}: {size_mb:.2f} MB")
        return backup_file
    else:
        print(f"   ❌ Erreur: {stderr}")
        return None


def backup_postgres(name: str, config: Dict) -> Optional[Path]:
    """Sauvegarde PostgreSQL via pg_dumpall"""
    container = config["container"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"{name}_{timestamp}.sql.gz"
    
    success, stdout, _ = run_command(["docker", "ps", "-q", "-f", f"name={container}"])
    if not success or not stdout.strip():
        print(f"   ⚠️ Conteneur {container} non trouvé")
        return None
    
    cmd = f"docker exec {container} pg_dumpall -U postgres | gzip > {backup_file}"
    success, _, stderr = run_command(["bash", "-c", cmd])
    
    if success and backup_file.exists() and backup_file.stat().st_size > 0:
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        print(f"   ✅ {name}: {size_mb:.2f} MB")
        return backup_file
    else:
        print(f"   ❌ Erreur PostgreSQL: {stderr}")
        return None


def get_s3_client():
    """Crée un client S3 pour Cloudflare R2"""
    import boto3
    from botocore.config import Config
    
    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        config=Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'}
        ),
        region_name=S3_REGION
    )


def upload_to_r2(files: List[Path]) -> bool:
    """Upload vers Cloudflare R2"""
    if not S3_ENDPOINT or not S3_ACCESS_KEY or not S3_SECRET_KEY:
        print("\n⚠️ Configuration R2 manquante. Backups conservés localement.")
        return False
    
    print(f"\n☁️ Upload vers R2 ({S3_BUCKET})...")
    
    try:
        s3 = get_s3_client()
        
        # Organiser par année/mois
        folder = datetime.now().strftime("%Y/%m")
        
        uploaded = 0
        for f in files:
            key = f"{folder}/{f.name}"
            try:
                s3.upload_file(str(f), S3_BUCKET, key)
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f"   ✅ {f.name} ({size_mb:.2f} MB)")
                uploaded += 1
            except Exception as e:
                print(f"   ❌ Erreur {f.name}: {e}")
        
        print(f"\n✅ {uploaded}/{len(files)} fichiers uploadés vers R2")
        return uploaded == len(files)
        
    except Exception as e:
        print(f"\n❌ Erreur connexion R2: {e}")
        return False


def list_r2_backups() -> List[Dict]:
    """Liste les backups sur R2"""
    if not S3_ENDPOINT or not S3_ACCESS_KEY:
        return []
    
    try:
        s3 = get_s3_client()
        response = s3.list_objects_v2(Bucket=S3_BUCKET)
        
        backups = []
        for obj in response.get('Contents', []):
            backups.append({
                'key': obj['Key'],
                'size_mb': obj['Size'] / (1024 * 1024),
                'modified': obj['LastModified'].isoformat()
            })
        return backups
    except Exception as e:
        print(f"Erreur liste R2: {e}")
        return []


def cleanup_old_backups(days: int = 7):
    """Supprime les backups locaux plus vieux que X jours"""
    now = time.time()
    cutoff = now - (days * 86400)
    
    count = 0
    for pattern in ["*.tar.gz", "*.sql.gz"]:
        for f in BACKUP_DIR.glob(pattern):
            if f.stat().st_mtime < cutoff:
                f.unlink()
                count += 1
    
    if count > 0:
        print(f"\n🧹 {count} anciens backups locaux supprimés")


def main():
    print("💾 Backup System v2.0 (Cloudflare R2)")
    print("=" * 50)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Mode liste
    if "--list" in sys.argv:
        print("\n☁️ Backups sur R2:")
        backups = list_r2_backups()
        if backups:
            total = 0
            for b in backups:
                print(f"   📄 {b['key']} ({b['size_mb']:.2f} MB)")
                total += b['size_mb']
            print(f"\n📊 Total sur R2: {total:.2f} MB")
        else:
            print("   (aucun backup)")
        return 0
    
    backup_files = []
    
    print("\n📦 Création des backups...")
    
    for name, config in BACKUP_TARGETS.items():
        if config["type"] == "directory":
            result = backup_directory(name, config)
        elif config["type"] == "database":
            result = backup_postgres(name, config)
        else:
            continue
        
        if result:
            backup_files.append(result)
    
    print(f"\n✅ {len(backup_files)} backups créés")
    
    total_size = sum(f.stat().st_size for f in backup_files) / (1024 * 1024)
    print(f"📊 Taille totale: {total_size:.2f} MB")
    
    # Upload vers R2 (par défaut activé si credentials présents)
    if "--no-upload" not in sys.argv:
        upload_to_r2(backup_files)
    
    # Nettoyage des anciens backups locaux
    if "--cleanup" in sys.argv:
        cleanup_old_backups()
    
    # Générer un résumé
    summary = {
        "timestamp": datetime.now().isoformat(),
        "backups": [
            {"name": f.stem, "size_mb": f.stat().st_size / (1024 * 1024), "path": str(f)}
            for f in backup_files
        ],
        "total_size_mb": total_size,
        "r2_bucket": S3_BUCKET
    }
    
    summary_file = BACKUP_DIR / "latest_backup.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n📁 Backups locaux: {BACKUP_DIR}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
