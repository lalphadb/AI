#!/usr/bin/env python3
"""
🧠 Self-Improvement Analyzer v2.0
Analyse avancée avec alertes Discord, tendances et actions automatiques
"""

import os
import json
import httpx
import asyncio
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# ============================================
# CONFIGURATION
# ============================================

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LOKI_URL = os.getenv("LOKI_URL", "http://localhost:3100")
MODEL = os.getenv("MODEL", "qwen2.5-coder:32b")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "")  # Optionnel
REPORTS_DIR = Path("/home/lalpha/projets/ai-tools/self-improvement/reports")
HISTORY_FILE = REPORTS_DIR / "history.json"

REPORTS_DIR.mkdir(exist_ok=True)

# Seuils d'alerte
THRESHOLDS = {
    "cpu_critical": 90,
    "cpu_warning": 75,
    "memory_critical": 90,
    "memory_warning": 80,
    "disk_critical": 90,
    "disk_warning": 80,
    "gpu_memory_critical": 95,
    "gpu_memory_warning": 85,
}


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    level: AlertLevel
    component: str
    message: str
    value: float
    threshold: float
    action: str


@dataclass
class HealthReport:
    timestamp: str
    score: int
    status: str
    metrics: Dict[str, Any]
    alerts: List[Dict]
    recommendations: List[str]
    auto_actions: List[str]
    trends: Dict[str, str]


# ============================================
# COLLECTE DES MÉTRIQUES
# ============================================

class MetricsCollector:
    """Collecte les métriques depuis Prometheus et le système"""
    
    def __init__(self):
        self.prometheus_url = PROMETHEUS_URL
        
    async def query_prometheus(self, promql: str) -> Optional[float]:
        """Exécute une requête PromQL"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.prometheus_url}/api/v1/query",
                    params={"query": promql}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("data", {}).get("result"):
                        return float(data["data"]["result"][0]["value"][1])
        except Exception:
            pass
        return None
    
    async def get_docker_info(self) -> Dict:
        """Récupère l'état des conteneurs Docker"""
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--format", "{{.Names}}|{{.Status}}|{{.State}}"],
                capture_output=True, text=True, timeout=10
            )
            containers = []
            running = 0
            stopped = 0
            unhealthy = 0
            
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|')
                    if len(parts) >= 3:
                        name, status, state = parts[0], parts[1], parts[2]
                        containers.append({
                            "name": name,
                            "status": status,
                            "state": state
                        })
                        if state == "running":
                            running += 1
                            if "unhealthy" in status.lower():
                                unhealthy += 1
                        else:
                            stopped += 1
            
            return {
                "total": len(containers),
                "running": running,
                "stopped": stopped,
                "unhealthy": unhealthy,
                "containers": containers
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def get_system_info(self) -> Dict:
        """Récupère les infos système directes"""
        info = {}
        
        # Uptime
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                info["uptime_days"] = round(uptime_seconds / 86400, 1)
        except:
            pass
        
        # Load average
        try:
            with open('/proc/loadavg', 'r') as f:
                loads = f.readline().split()[:3]
                info["load_1m"] = float(loads[0])
                info["load_5m"] = float(loads[1])
                info["load_15m"] = float(loads[2])
        except:
            pass
        
        # GPU info via nvidia-smi
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu", 
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(', ')
                if len(parts) >= 4:
                    info["gpu_util"] = float(parts[0])
                    info["gpu_mem_used"] = float(parts[1])
                    info["gpu_mem_total"] = float(parts[2])
                    info["gpu_temp"] = float(parts[3])
                    info["gpu_mem_percent"] = (info["gpu_mem_used"] / info["gpu_mem_total"]) * 100
        except:
            pass
        
        return info
    
    async def collect_all(self) -> Dict[str, Any]:
        """Collecte toutes les métriques"""
        metrics = {}
        
        # Métriques Prometheus
        prom_queries = {
            "cpu_percent": '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
            "memory_percent": '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100',
            "disk_root_percent": '(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100',
            "disk_ollama_percent": '(1 - (node_filesystem_avail_bytes{mountpoint="/mnt/ollama-models"} / node_filesystem_size_bytes{mountpoint="/mnt/ollama-models"})) * 100',
            "network_rx_rate": 'rate(node_network_receive_bytes_total{device="eth0"}[5m])',
            "network_tx_rate": 'rate(node_network_transmit_bytes_total{device="eth0"}[5m])',
        }
        
        for name, query in prom_queries.items():
            value = await self.query_prometheus(query)
            if value is not None:
                metrics[name] = round(value, 2)
        
        # Docker
        docker_info = await self.get_docker_info()
        metrics["docker"] = docker_info
        
        # Système
        sys_info = await self.get_system_info()
        metrics.update(sys_info)
        
        metrics["collected_at"] = datetime.now().isoformat()
        
        return metrics


# ============================================
# ANALYSE ET ALERTES
# ============================================

class HealthAnalyzer:
    """Analyse les métriques et génère des alertes"""
    
    def __init__(self, metrics: Dict):
        self.metrics = metrics
        self.alerts: List[Alert] = []
        self.score = 100
    
    def check_thresholds(self):
        """Vérifie les seuils et génère des alertes"""
        
        # CPU
        cpu = self.metrics.get("cpu_percent", 0)
        if cpu >= THRESHOLDS["cpu_critical"]:
            self.alerts.append(Alert(
                AlertLevel.CRITICAL, "CPU", 
                f"CPU critique: {cpu:.1f}%", 
                cpu, THRESHOLDS["cpu_critical"],
                "Identifier les processus gourmands avec htop"
            ))
            self.score -= 20
        elif cpu >= THRESHOLDS["cpu_warning"]:
            self.alerts.append(Alert(
                AlertLevel.WARNING, "CPU",
                f"CPU élevé: {cpu:.1f}%",
                cpu, THRESHOLDS["cpu_warning"],
                "Surveiller l'évolution"
            ))
            self.score -= 5
        
        # Mémoire
        mem = self.metrics.get("memory_percent", 0)
        if mem >= THRESHOLDS["memory_critical"]:
            self.alerts.append(Alert(
                AlertLevel.CRITICAL, "RAM",
                f"Mémoire critique: {mem:.1f}%",
                mem, THRESHOLDS["memory_critical"],
                "Redémarrer les conteneurs gourmands ou ajouter du swap"
            ))
            self.score -= 20
        elif mem >= THRESHOLDS["memory_warning"]:
            self.alerts.append(Alert(
                AlertLevel.WARNING, "RAM",
                f"Mémoire élevée: {mem:.1f}%",
                mem, THRESHOLDS["memory_warning"],
                "Surveiller l'évolution"
            ))
            self.score -= 5
        
        # Disque système
        disk = self.metrics.get("disk_root_percent", 0)
        if disk >= THRESHOLDS["disk_critical"]:
            self.alerts.append(Alert(
                AlertLevel.CRITICAL, "Disque",
                f"Disque système critique: {disk:.1f}%",
                disk, THRESHOLDS["disk_critical"],
                "Nettoyer avec: docker system prune -af"
            ))
            self.score -= 25
        elif disk >= THRESHOLDS["disk_warning"]:
            self.alerts.append(Alert(
                AlertLevel.WARNING, "Disque",
                f"Disque système élevé: {disk:.1f}%",
                disk, THRESHOLDS["disk_warning"],
                "Planifier un nettoyage"
            ))
            self.score -= 10
        
        # GPU Mémoire
        gpu_mem = self.metrics.get("gpu_mem_percent", 0)
        if gpu_mem >= THRESHOLDS["gpu_memory_critical"]:
            self.alerts.append(Alert(
                AlertLevel.CRITICAL, "GPU",
                f"VRAM critique: {gpu_mem:.1f}%",
                gpu_mem, THRESHOLDS["gpu_memory_critical"],
                "Réduire la taille du modèle ou les requêtes concurrentes"
            ))
            self.score -= 15
        elif gpu_mem >= THRESHOLDS["gpu_memory_warning"]:
            self.alerts.append(Alert(
                AlertLevel.WARNING, "GPU",
                f"VRAM élevée: {gpu_mem:.1f}%",
                gpu_mem, THRESHOLDS["gpu_memory_warning"],
                "Surveiller lors de charges lourdes"
            ))
            self.score -= 5
        
        # Docker conteneurs unhealthy
        docker = self.metrics.get("docker", {})
        if docker.get("unhealthy", 0) > 0:
            self.alerts.append(Alert(
                AlertLevel.WARNING, "Docker",
                f"{docker['unhealthy']} conteneur(s) unhealthy",
                docker['unhealthy'], 0,
                "Vérifier avec: docker ps --filter health=unhealthy"
            ))
            self.score -= 10
        
        # Température GPU
        gpu_temp = self.metrics.get("gpu_temp", 0)
        if gpu_temp >= 85:
            self.alerts.append(Alert(
                AlertLevel.CRITICAL, "GPU Temp",
                f"GPU surchauffe: {gpu_temp}°C",
                gpu_temp, 85,
                "Vérifier ventilation, réduire charge"
            ))
            self.score -= 15
        elif gpu_temp >= 75:
            self.alerts.append(Alert(
                AlertLevel.WARNING, "GPU Temp",
                f"GPU chaud: {gpu_temp}°C",
                gpu_temp, 75,
                "Surveiller température"
            ))
            self.score -= 5
        
        self.score = max(0, self.score)
    
    def get_status(self) -> str:
        """Retourne le status global"""
        if self.score >= 90:
            return "excellent"
        elif self.score >= 75:
            return "healthy"
        elif self.score >= 50:
            return "degraded"
        else:
            return "critical"
    
    def has_critical(self) -> bool:
        """Vérifie s'il y a des alertes critiques"""
        return any(a.level == AlertLevel.CRITICAL for a in self.alerts)


# ============================================
# ANALYSE LLM
# ============================================

async def get_llm_recommendations(metrics: Dict, alerts: List[Alert]) -> List[str]:
    """Demande au LLM des recommandations basées sur les métriques"""
    
    prompt = f"""Tu es un expert DevOps analysant un serveur Ubuntu avec infrastructure IA.

## Métriques actuelles:
- CPU: {metrics.get('cpu_percent', 'N/A')}%
- RAM: {metrics.get('memory_percent', 'N/A')}%
- Disque /: {metrics.get('disk_root_percent', 'N/A')}%
- Disque Ollama: {metrics.get('disk_ollama_percent', 'N/A')}%
- GPU Utilisation: {metrics.get('gpu_util', 'N/A')}%
- GPU VRAM: {metrics.get('gpu_mem_percent', 'N/A')}%
- GPU Temp: {metrics.get('gpu_temp', 'N/A')}°C
- Load Average: {metrics.get('load_1m', 'N/A')}
- Conteneurs Docker: {metrics.get('docker', {}).get('running', 'N/A')} running, {metrics.get('docker', {}).get('stopped', 'N/A')} stopped

## Alertes actuelles:
{chr(10).join([f"- [{a.level.value.upper()}] {a.message}" for a in alerts]) if alerts else "Aucune alerte"}

Génère 3-5 recommandations concrètes et actionnables pour optimiser ce serveur.
Format: Une recommandation par ligne, commençant par un verbe d'action.
Sois concis et précis."""

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 500}
                }
            )
            if resp.status_code == 200:
                text = resp.json().get("response", "")
                # Parse les lignes comme recommandations
                recommendations = []
                for line in text.strip().split('\n'):
                    line = line.strip()
                    if line and len(line) > 10:
                        # Nettoyer les préfixes courants
                        for prefix in ['- ', '• ', '* ', '1. ', '2. ', '3. ', '4. ', '5. ']:
                            if line.startswith(prefix):
                                line = line[len(prefix):]
                        recommendations.append(line)
                return recommendations[:5]
    except Exception as e:
        return [f"Erreur LLM: {str(e)}"]
    
    return []


# ============================================
# TENDANCES (HISTORIQUE)
# ============================================

def load_history() -> List[Dict]:
    """Charge l'historique des rapports"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except:
            pass
    return []


def save_to_history(report: Dict):
    """Sauvegarde dans l'historique"""
    history = load_history()
    history.append({
        "timestamp": report["timestamp"],
        "score": report["score"],
        "cpu": report["metrics"].get("cpu_percent"),
        "memory": report["metrics"].get("memory_percent"),
        "disk": report["metrics"].get("disk_root_percent"),
        "gpu_mem": report["metrics"].get("gpu_mem_percent"),
        "alerts_count": len(report["alerts"])
    })
    # Garder les 30 derniers jours
    history = history[-30:]
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


def calculate_trends(current: Dict) -> Dict[str, str]:
    """Calcule les tendances vs historique"""
    history = load_history()
    if len(history) < 2:
        return {}
    
    trends = {}
    recent = history[-7:] if len(history) >= 7 else history  # Derniers 7 jours
    
    for metric in ["cpu", "memory", "disk", "score"]:
        current_val = current.get("metrics", {}).get(f"{metric}_percent") if metric != "score" else current.get("score")
        if current_val is None:
            continue
        
        avg_past = sum(h.get(metric, 0) or 0 for h in recent) / len(recent)
        
        if current_val > avg_past * 1.1:
            trends[metric] = "↑ hausse"
        elif current_val < avg_past * 0.9:
            trends[metric] = "↓ baisse"
        else:
            trends[metric] = "→ stable"
    
    return trends


# ============================================
# NOTIFICATIONS DISCORD
# ============================================

async def send_discord_alert(report: Dict, has_critical: bool):
    """Envoie une alerte Discord si configuré"""
    if not DISCORD_WEBHOOK:
        return
    
    # Couleur selon gravité
    if has_critical:
        color = 0xFF0000  # Rouge
        title = "🚨 ALERTE CRITIQUE - lalpha-server-1"
    elif report["score"] < 75:
        color = 0xFFA500  # Orange
        title = "⚠️ ATTENTION - lalpha-server-1"
    else:
        color = 0x00FF00  # Vert
        title = "✅ Rapport quotidien - lalpha-server-1"
    
    # Construire le message
    fields = [
        {"name": "Score", "value": f"**{report['score']}/100** ({report['status']})", "inline": True},
        {"name": "CPU", "value": f"{report['metrics'].get('cpu_percent', 'N/A')}%", "inline": True},
        {"name": "RAM", "value": f"{report['metrics'].get('memory_percent', 'N/A')}%", "inline": True},
    ]
    
    if report.get("alerts"):
        alerts_text = "\n".join([f"• {a['message']}" for a in report["alerts"][:5]])
        fields.append({"name": "Alertes", "value": alerts_text, "inline": False})
    
    if report.get("recommendations"):
        recs_text = "\n".join([f"• {r[:80]}" for r in report["recommendations"][:3]])
        fields.append({"name": "Recommandations", "value": recs_text, "inline": False})
    
    embed = {
        "title": title,
        "color": color,
        "fields": fields,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "Self-Improvement v2.0"}
    }
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(DISCORD_WEBHOOK, json={"embeds": [embed]})
    except Exception as e:
        print(f"⚠️ Erreur Discord: {e}")


# ============================================
# MAIN
# ============================================

async def main(quick_mode: bool = False, force_alert: bool = False):
    """Exécution principale"""
    print("🧠 Self-Improvement Analyzer v2.0")
    print("=" * 50)
    print()
    
    # 1. Collecte des métriques
    print("📊 Collecte des métriques...")
    collector = MetricsCollector()
    metrics = await collector.collect_all()
    print(f"   ✅ {len(metrics)} métriques collectées")
    
    # 2. Analyse et alertes
    print("\n🔍 Analyse des seuils...")
    analyzer = HealthAnalyzer(metrics)
    analyzer.check_thresholds()
    print(f"   ✅ Score: {analyzer.score}/100 ({analyzer.get_status()})")
    print(f"   ✅ {len(analyzer.alerts)} alerte(s)")
    
    # 3. Recommandations LLM (sauf mode quick)
    recommendations = []
    if not quick_mode:
        print("\n🤖 Analyse LLM...")
        recommendations = await get_llm_recommendations(metrics, analyzer.alerts)
        print(f"   ✅ {len(recommendations)} recommandations")
    
    # 4. Construire le rapport
    report = {
        "timestamp": datetime.now().isoformat(),
        "score": analyzer.score,
        "status": analyzer.get_status(),
        "metrics": metrics,
        "alerts": [asdict(a) for a in analyzer.alerts],
        "recommendations": recommendations,
        "auto_actions": [a.action for a in analyzer.alerts],
        "trends": {}
    }
    
    # 5. Tendances
    report["trends"] = calculate_trends(report)
    
    # 6. Sauvegarder
    report_file = REPORTS_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n💾 Rapport: {report_file}")
    
    # Sauvegarder dans l'historique
    save_to_history(report)
    
    # 7. Afficher le résumé
    print("\n" + "=" * 50)
    print(f"📈 RÉSUMÉ")
    print("=" * 50)
    
    status_emoji = {"excellent": "🌟", "healthy": "✅", "degraded": "⚠️", "critical": "🚨"}
    print(f"\n{status_emoji.get(report['status'], '❓')} Status: {report['status'].upper()} ({report['score']}/100)")
    
    print(f"\n📊 Métriques clés:")
    print(f"   CPU:    {metrics.get('cpu_percent', 'N/A')}%")
    print(f"   RAM:    {metrics.get('memory_percent', 'N/A')}%")
    print(f"   Disque: {metrics.get('disk_root_percent', 'N/A')}%")
    if metrics.get('gpu_util') is not None:
        print(f"   GPU:    {metrics.get('gpu_util')}% (VRAM: {metrics.get('gpu_mem_percent', 'N/A'):.1f}%, Temp: {metrics.get('gpu_temp')}°C)")
    
    docker = metrics.get("docker", {})
    if docker:
        print(f"   Docker: {docker.get('running', 0)} running, {docker.get('stopped', 0)} stopped")
    
    if analyzer.alerts:
        print(f"\n🚨 Alertes ({len(analyzer.alerts)}):")
        for alert in analyzer.alerts:
            level_emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}
            print(f"   {level_emoji.get(alert.level.value, '⚪')} [{alert.level.value.upper()}] {alert.message}")
            print(f"      → Action: {alert.action}")
    
    if recommendations:
        print(f"\n💡 Recommandations LLM:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
    
    if report["trends"]:
        print(f"\n📈 Tendances (vs 7 derniers jours):")
        for metric, trend in report["trends"].items():
            print(f"   {metric}: {trend}")
    
    # 8. Envoyer alerte Discord si nécessaire
    if DISCORD_WEBHOOK and (analyzer.has_critical() or force_alert):
        print("\n📤 Envoi alerte Discord...")
        await send_discord_alert(report, analyzer.has_critical())
        print("   ✅ Envoyé")
    
    print("\n" + "=" * 50)
    print("✅ Analyse terminée")
    
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Self-Improvement Analyzer v2.0")
    parser.add_argument("--quick", action="store_true", help="Mode rapide (sans LLM)")
    parser.add_argument("--alert", action="store_true", help="Forcer l'envoi Discord")
    args = parser.parse_args()
    
    asyncio.run(main(quick_mode=args.quick, force_alert=args.alert))
