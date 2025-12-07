#!/usr/bin/env python3
"""
🔄 Auto-Actions Module
Actions automatiques en réponse aux alertes
"""

import subprocess
import shutil
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import json

LOG_FILE = Path("/home/lalpha/projets/ai-tools/self-improvement/actions.log")

def log_action(action: str, result: str, success: bool):
    """Log une action"""
    timestamp = datetime.now().isoformat()
    status = "✅" if success else "❌"
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] {status} {action}: {result}\n")
    print(f"   {status} {action}: {result}")


class AutoActions:
    """Gestionnaire d'actions automatiques"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.actions_taken = []
    
    def restart_container(self, container_name: str) -> Tuple[bool, str]:
        """Redémarre un conteneur Docker"""
        if self.dry_run:
            return True, f"[DRY-RUN] Redémarrerait {container_name}"
        
        try:
            result = subprocess.run(
                ["docker", "restart", container_name],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                log_action(f"restart_container({container_name})", "OK", True)
                self.actions_taken.append(f"Redémarré: {container_name}")
                return True, f"Conteneur {container_name} redémarré"
            else:
                log_action(f"restart_container({container_name})", result.stderr, False)
                return False, result.stderr
        except Exception as e:
            log_action(f"restart_container({container_name})", str(e), False)
            return False, str(e)
    
    def restart_unhealthy_containers(self) -> List[str]:
        """Redémarre tous les conteneurs unhealthy"""
        restarted = []
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "health=unhealthy", "--format", "{{.Names}}"],
                capture_output=True, text=True
            )
            unhealthy = [c.strip() for c in result.stdout.strip().split('\n') if c.strip()]
            
            for container in unhealthy:
                success, msg = self.restart_container(container)
                if success:
                    restarted.append(container)
        except Exception as e:
            log_action("restart_unhealthy_containers", str(e), False)
        
        return restarted
    
    def cleanup_docker(self) -> Tuple[bool, str]:
        """Nettoie les ressources Docker inutilisées"""
        if self.dry_run:
            return True, "[DRY-RUN] Nettoierait les ressources Docker"
        
        try:
            # Nettoyer images dangling
            result = subprocess.run(
                ["docker", "image", "prune", "-f"],
                capture_output=True, text=True, timeout=120
            )
            
            # Nettoyer volumes orphelins
            subprocess.run(
                ["docker", "volume", "prune", "-f"],
                capture_output=True, text=True, timeout=120
            )
            
            # Récupérer l'espace libéré
            space_freed = "Espace libéré (voir logs Docker)"
            log_action("cleanup_docker", space_freed, True)
            self.actions_taken.append(f"Nettoyage Docker: {space_freed}")
            return True, space_freed
        except Exception as e:
            log_action("cleanup_docker", str(e), False)
            return False, str(e)
    
    def cleanup_old_logs(self, days: int = 7) -> Tuple[bool, str]:
        """Supprime les vieux fichiers de log"""
        if self.dry_run:
            return True, f"[DRY-RUN] Supprimerait logs > {days} jours"
        
        cleaned = 0
        total_size = 0
        log_dirs = [
            "/var/log",
            "/home/lalpha/projets/ai-tools/self-improvement/reports"
        ]
        
        try:
            # Nettoyer les vieux rapports (garder les 30 derniers)
            reports_dir = Path("/home/lalpha/projets/ai-tools/self-improvement/reports")
            reports = sorted(reports_dir.glob("report_*.json"), reverse=True)
            
            for old_report in reports[30:]:  # Garder les 30 derniers
                size = old_report.stat().st_size
                old_report.unlink()
                cleaned += 1
                total_size += size
            
            result = f"Supprimé {cleaned} fichiers ({total_size / 1024:.1f} KB)"
            log_action("cleanup_old_logs", result, True)
            self.actions_taken.append(result)
            return True, result
        except Exception as e:
            log_action("cleanup_old_logs", str(e), False)
            return False, str(e)
    
    def cleanup_disk_space(self, threshold_gb: float = 50) -> Tuple[bool, str]:
        """Libère de l'espace disque si nécessaire"""
        if self.dry_run:
            return True, "[DRY-RUN] Libérerait de l'espace disque"
        
        actions = []
        
        # 1. Nettoyer apt cache
        try:
            subprocess.run(["apt-get", "clean"], capture_output=True, timeout=30)
            actions.append("apt cache")
        except:
            pass
        
        # 2. Nettoyer journal systemd (garder 500M)
        try:
            subprocess.run(
                ["journalctl", "--vacuum-size=500M"],
                capture_output=True, timeout=60
            )
            actions.append("journalctl")
        except:
            pass
        
        # 3. Nettoyer Docker
        self.cleanup_docker()
        actions.append("docker")
        
        # 4. Nettoyer vieux logs
        self.cleanup_old_logs()
        actions.append("old logs")
        
        result = f"Nettoyé: {', '.join(actions)}"
        log_action("cleanup_disk_space", result, True)
        return True, result
    
    def restart_service(self, service_name: str) -> Tuple[bool, str]:
        """Redémarre un service systemd"""
        if self.dry_run:
            return True, f"[DRY-RUN] Redémarrerait {service_name}"
        
        try:
            result = subprocess.run(
                ["systemctl", "restart", service_name],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                log_action(f"restart_service({service_name})", "OK", True)
                self.actions_taken.append(f"Service redémarré: {service_name}")
                return True, f"Service {service_name} redémarré"
            else:
                return False, result.stderr
        except Exception as e:
            log_action(f"restart_service({service_name})", str(e), False)
            return False, str(e)
    
    def execute_action(self, action_type: str, params: Dict = None) -> Tuple[bool, str]:
        """Exécute une action par type"""
        params = params or {}
        
        actions_map = {
            "restart_container": lambda: self.restart_container(params.get("name", "")),
            "restart_unhealthy": lambda: (True, f"Redémarrés: {self.restart_unhealthy_containers()}"),
            "cleanup_docker": lambda: self.cleanup_docker(),
            "cleanup_logs": lambda: self.cleanup_old_logs(params.get("days", 7)),
            "cleanup_disk": lambda: self.cleanup_disk_space(),
            "restart_service": lambda: self.restart_service(params.get("name", "")),
        }
        
        action_fn = actions_map.get(action_type)
        if action_fn:
            return action_fn()
        else:
            return False, f"Action inconnue: {action_type}"
    
    def get_summary(self) -> str:
        """Retourne un résumé des actions"""
        if not self.actions_taken:
            return "Aucune action effectuée"
        return "\n".join(f"  • {a}" for a in self.actions_taken)


# Test
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Mode simulation")
    parser.add_argument("--action", type=str, help="Action à exécuter")
    args = parser.parse_args()
    
    actions = AutoActions(dry_run=args.dry_run)
    
    if args.action:
        success, msg = actions.execute_action(args.action)
        print(f"{'✅' if success else '❌'} {msg}")
    else:
        print("Actions disponibles:")
        print("  --action restart_unhealthy")
        print("  --action cleanup_docker")
        print("  --action cleanup_logs")
        print("  --action cleanup_disk")
