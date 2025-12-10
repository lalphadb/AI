#!/usr/bin/env python3
"""
💾 Script de backup hebdomadaire - Exécuté par cron
Usage: python3 weekly_backup.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules import backup_tools

def main():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] 💾 Démarrage backup hebdomadaire")
    
    results = {
        "timestamp": timestamp,
        "backup_full": None,
        "success": False
    }
    
    # Backup complet
    print("[INFO] Exécution du backup complet...")
    results["backup_full"] = backup_tools.backup_full(include_secrets=False)
    
    # Nettoyage des anciens backups (> 30 jours)
    print("[INFO] Nettoyage des anciens backups...")
    cleanup_result = backup_tools.cleanup_old_backups(days=30)
    results["cleanup"] = cleanup_result
    
    # Vérifier le succès global
    results["success"] = (
        results["backup_full"] and 
        results["backup_full"].get("success", False)
    )
    
    # Sauvegarder le rapport
    reports_dir = Path(__file__).parent.parent / "logs" / "backup_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = reports_dir / f"backup_{datetime.now().strftime('%Y%m%d')}.json"
    report_file.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str))
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Backup terminé")
    print(f"[INFO] Rapport: {report_file}")
    
    if results["success"]:
        summary = results["backup_full"].get("summary", {})
        print(f"[INFO] Backups réussis: {summary.get('successful', 0)}/{summary.get('total_backups', 0)}")
    else:
        print("[ERROR] Échec du backup!")
        sys.exit(1)

if __name__ == "__main__":
    main()
