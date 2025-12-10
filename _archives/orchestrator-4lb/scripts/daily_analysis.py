#!/usr/bin/env python3
"""
🔄 Script d'analyse quotidienne - Exécuté par cron
Usage: python3 daily_analysis.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules import self_improve_tools, backup_tools

def main():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] 🔄 Démarrage analyse quotidienne")
    
    results = {
        "timestamp": timestamp,
        "logs_analysis": None,
        "anomalies": None,
        "suggestions": None,
        "backup_configs": None
    }
    
    # 1. Analyser les logs Docker
    print("[INFO] Analyse des logs Docker...")
    results["logs_analysis"] = self_improve_tools.self_improve_analyze_logs(
        source="docker",
        focus="errors and warnings"
    )
    
    # 2. Détecter les anomalies
    print("[INFO] Détection des anomalies...")
    results["anomalies"] = self_improve_tools.self_improve_anomalies()
    
    # 3. Générer des suggestions
    print("[INFO] Génération des suggestions...")
    results["suggestions"] = self_improve_tools.self_improve_suggestions()
    
    # 4. Backup des configs (quotidien)
    print("[INFO] Backup des configurations...")
    results["backup_configs"] = backup_tools.backup_configs(include_secrets=False)
    
    # Sauvegarder le rapport
    reports_dir = Path(__file__).parent.parent / "logs" / "daily_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = reports_dir / f"report_{datetime.now().strftime('%Y%m%d')}.json"
    report_file.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str))
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Analyse terminée")
    print(f"[INFO] Rapport: {report_file}")
    
    # Résumé des alertes
    if results["anomalies"] and results["anomalies"].get("success"):
        analysis = results["anomalies"].get("analysis", {})
        if analysis.get("overall_status") in ["warning", "critical"]:
            print(f"[ALERT] État système: {analysis.get('overall_status')}")
            for anomaly in analysis.get("anomalies", [])[:5]:
                print(f"  - [{anomaly.get('severity', 'unknown')}] {anomaly.get('description', 'N/A')}")

if __name__ == "__main__":
    main()
