"""
🧠 Module Self-Improve - Auto-amélioration avec IA

Outils disponibles:
- self_improve_analyze_logs: Analyse des logs avec Ollama
- self_improve_anomalies: Détection d'anomalies
- self_improve_suggestions: Suggestions d'optimisation
"""

import os
import subprocess
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
import requests

from config.settings import (
    OLLAMA_HOST, OLLAMA_MODEL, LOGS_DIR,
    INFRA_DIR, ANOMALY_THRESHOLD
)

logger = logging.getLogger(__name__)


class SelfImproveTools:
    """Outils d'auto-amélioration avec IA locale"""
    
    def __init__(self):
        self.ollama_host = OLLAMA_HOST
        self.model = OLLAMA_MODEL
        self.analysis_history: List[Dict] = []
    
    def _call_ollama(self, prompt: str, system: Optional[str] = None) -> Dict[str, Any]:
        """Appeler l'API Ollama"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            
            if system:
                payload["system"] = system
            
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "response": result.get("response", ""),
                    "model": self.model,
                    "eval_count": result.get("eval_count", 0)
                }
            else:
                return {
                    "success": False,
                    "error": f"Ollama HTTP {response.status_code}: {response.text}"
                }
                
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": f"Impossible de se connecter à Ollama ({self.ollama_host})"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_recent_logs(self, source: str, lines: int = 200) -> str:
        """Récupérer les logs récents"""
        logs = ""
        
        if source == "docker":
            # Logs Docker
            result = subprocess.run(
                ["docker", "logs", "--tail", str(lines), "--timestamps", "traefik"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                logs += f"=== TRAEFIK LOGS ===\n{result.stdout}\n"
            
            # Logs des autres conteneurs importants
            for container in ["open-webui", "prometheus", "postgres"]:
                result = subprocess.run(
                    ["docker", "logs", "--tail", "50", "--timestamps", container],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    logs += f"=== {container.upper()} LOGS ===\n{result.stdout}\n"
        
        elif source == "system":
            # Logs système via journalctl
            result = subprocess.run(
                ["journalctl", "--since", "1 hour ago", "-n", str(lines), "--no-pager"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                logs = result.stdout
        
        elif source == "ollama":
            # Logs Ollama
            result = subprocess.run(
                ["journalctl", "-u", "ollama", "-n", str(lines), "--no-pager"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                logs = result.stdout
        
        return logs[:15000]  # Limiter la taille pour Ollama
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """Récupérer les métriques système"""
        metrics = {}
        
        # CPU
        result = subprocess.run(
            ["grep", "-c", "^processor", "/proc/cpuinfo"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            metrics["cpu_cores"] = int(result.stdout.strip())
        
        # Load average
        result = subprocess.run(["cat", "/proc/loadavg"], capture_output=True, text=True)
        if result.returncode == 0:
            metrics["load_avg"] = result.stdout.strip().split()[:3]
        
        # Mémoire
        result = subprocess.run(["free", "-m"], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                mem_parts = lines[1].split()
                metrics["memory"] = {
                    "total_mb": int(mem_parts[1]),
                    "used_mb": int(mem_parts[2]),
                    "free_mb": int(mem_parts[3]),
                    "usage_percent": round(int(mem_parts[2]) / int(mem_parts[1]) * 100, 1)
                }
        
        # Disque
        result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                disk_parts = lines[1].split()
                metrics["disk"] = {
                    "total": disk_parts[1],
                    "used": disk_parts[2],
                    "available": disk_parts[3],
                    "usage_percent": disk_parts[4]
                }
        
        # GPU (si disponible)
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", 
             "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            gpu_parts = result.stdout.strip().split(",")
            metrics["gpu"] = {
                "utilization_percent": int(gpu_parts[0].strip()),
                "memory_used_mb": int(gpu_parts[1].strip()),
                "memory_total_mb": int(gpu_parts[2].strip())
            }
        
        # Docker containers
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}: {{.Status}}"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            metrics["docker_containers"] = result.stdout.strip().split("\n")
        
        return metrics
    
    # === 1. ANALYZE LOGS ===
    def self_improve_analyze_logs(
        self, 
        source: str = "docker",
        focus: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyser les logs avec Ollama
        
        Args:
            source: Source des logs (docker, system, ollama)
            focus: Point d'attention spécifique
            
        Returns:
            Dict avec l'analyse et les recommandations
        """
        try:
            # Récupérer les logs
            logs = self._get_recent_logs(source)
            
            if not logs.strip():
                return {
                    "success": False,
                    "error": f"Aucun log disponible pour {source}"
                }
            
            # Construire le prompt
            system_prompt = """Tu es un expert DevOps qui analyse les logs système.
Tu dois:
1. Identifier les erreurs et warnings
2. Détecter les patterns anormaux
3. Proposer des actions correctives
4. Évaluer la santé globale (score 0-100)

Réponds en JSON structuré avec: 
{
  "health_score": int,
  "errors": ["liste des erreurs"],
  "warnings": ["liste des warnings"],
  "anomalies": ["patterns anormaux"],
  "recommendations": ["actions à prendre"],
  "summary": "résumé en une phrase"
}"""
            
            focus_text = f"\n\nFocus particulier sur: {focus}" if focus else ""
            
            prompt = f"""Analyse les logs suivants:{focus_text}

{logs}

Donne ton analyse en JSON."""
            
            # Appeler Ollama
            result = self._call_ollama(prompt, system_prompt)
            
            if not result["success"]:
                return result
            
            # Parser la réponse JSON
            response_text = result["response"]
            
            # Extraire le JSON de la réponse
            try:
                # Chercher le JSON dans la réponse
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = {"raw_response": response_text}
            except json.JSONDecodeError:
                analysis = {"raw_response": response_text}
            
            # Stocker dans l'historique
            self.analysis_history.append({
                "timestamp": datetime.now().isoformat(),
                "source": source,
                "analysis": analysis
            })
            
            # Sauvegarder le rapport
            report_path = LOGS_DIR / "analysis" / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(analysis, indent=2, ensure_ascii=False))
            
            logger.info(f"Analyse logs {source}: score={analysis.get('health_score', 'N/A')}")
            
            return {
                "success": True,
                "source": source,
                "analysis": analysis,
                "model_used": self.model,
                "report_path": str(report_path)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # === 2. DETECT ANOMALIES ===
    def self_improve_anomalies(self) -> Dict[str, Any]:
        """
        Détecter les anomalies système avec métriques
        
        Returns:
            Dict avec les anomalies détectées et recommandations
        """
        try:
            # Récupérer les métriques
            metrics = self._get_system_metrics()
            
            # Construire le prompt
            system_prompt = """Tu es un expert en monitoring et détection d'anomalies.
Analyse les métriques système et détecte les problèmes potentiels.

Réponds en JSON:
{
  "anomalies": [
    {"type": "cpu|memory|disk|gpu|docker", "severity": "low|medium|high|critical", "description": "..."}
  ],
  "alerts": ["alertes immédiates"],
  "optimizations": ["suggestions d'optimisation"],
  "overall_status": "healthy|warning|critical"
}"""
            
            prompt = f"""Analyse ces métriques système:

{json.dumps(metrics, indent=2)}

Détecte les anomalies et problèmes potentiels."""
            
            # Appeler Ollama
            result = self._call_ollama(prompt, system_prompt)
            
            if not result["success"]:
                # Fallback: détection basique sans IA
                anomalies = self._basic_anomaly_detection(metrics)
                return {
                    "success": True,
                    "metrics": metrics,
                    "anomalies": anomalies,
                    "method": "basic",
                    "warning": "Ollama non disponible, analyse basique utilisée"
                }
            
            # Parser la réponse
            response_text = result["response"]
            
            try:
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = {"raw_response": response_text}
            except json.JSONDecodeError:
                analysis = {"raw_response": response_text}
            
            logger.info(f"Détection anomalies: status={analysis.get('overall_status', 'unknown')}")
            
            return {
                "success": True,
                "metrics": metrics,
                "analysis": analysis,
                "model_used": self.model,
                "method": "ai"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _basic_anomaly_detection(self, metrics: Dict) -> List[Dict]:
        """Détection d'anomalies basique (sans IA)"""
        anomalies = []
        
        # CPU load
        if "load_avg" in metrics and metrics.get("cpu_cores"):
            load_1m = float(metrics["load_avg"][0])
            cores = metrics["cpu_cores"]
            if load_1m > cores * 0.8:
                anomalies.append({
                    "type": "cpu",
                    "severity": "high" if load_1m > cores else "medium",
                    "description": f"Load average élevé: {load_1m} (cores: {cores})"
                })
        
        # Mémoire
        if "memory" in metrics:
            usage = metrics["memory"].get("usage_percent", 0)
            if usage > 90:
                anomalies.append({
                    "type": "memory",
                    "severity": "critical",
                    "description": f"Mémoire critique: {usage}%"
                })
            elif usage > 80:
                anomalies.append({
                    "type": "memory",
                    "severity": "high",
                    "description": f"Mémoire élevée: {usage}%"
                })
        
        # Disque
        if "disk" in metrics:
            usage_str = metrics["disk"].get("usage_percent", "0%")
            usage = int(usage_str.replace("%", ""))
            if usage > 90:
                anomalies.append({
                    "type": "disk",
                    "severity": "critical",
                    "description": f"Disque critique: {usage}%"
                })
            elif usage > 80:
                anomalies.append({
                    "type": "disk",
                    "severity": "high",
                    "description": f"Disque élevé: {usage}%"
                })
        
        # GPU
        if "gpu" in metrics:
            gpu_util = metrics["gpu"].get("utilization_percent", 0)
            gpu_mem = metrics["gpu"].get("memory_used_mb", 0) / max(metrics["gpu"].get("memory_total_mb", 1), 1) * 100
            
            if gpu_mem > 95:
                anomalies.append({
                    "type": "gpu",
                    "severity": "high",
                    "description": f"VRAM proche de la saturation: {gpu_mem:.1f}%"
                })
        
        return anomalies
    
    # === 3. GENERATE SUGGESTIONS ===
    def self_improve_suggestions(self, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Générer des suggestions d'amélioration
        
        Args:
            context: Contexte additionnel pour les suggestions
            
        Returns:
            Dict avec les suggestions d'amélioration
        """
        try:
            # Collecter les informations
            metrics = self._get_system_metrics()
            docker_logs = self._get_recent_logs("docker", lines=100)
            
            # Construire le prompt
            system_prompt = """Tu es un consultant DevOps expert.
Propose des améliorations pour optimiser l'infrastructure.

Catégories:
- Performance (CPU, mémoire, GPU)
- Sécurité (ports, accès, logs)
- Maintenance (backups, mises à jour)
- Architecture (conteneurs, services)

Réponds en JSON:
{
  "suggestions": [
    {
      "category": "...",
      "priority": "low|medium|high",
      "title": "...",
      "description": "...",
      "action": "commande ou étape à suivre",
      "impact": "..."
    }
  ],
  "quick_wins": ["actions rapides à fort impact"],
  "long_term": ["améliorations à planifier"]
}"""
            
            context_text = f"\n\nContexte additionnel: {context}" if context else ""
            
            prompt = f"""Analyse cette infrastructure et propose des améliorations:{context_text}

MÉTRIQUES:
{json.dumps(metrics, indent=2)}

LOGS DOCKER (extrait):
{docker_logs[:5000]}

Génère des suggestions d'amélioration."""
            
            # Appeler Ollama
            result = self._call_ollama(prompt, system_prompt)
            
            if not result["success"]:
                return result
            
            # Parser la réponse
            response_text = result["response"]
            
            try:
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    suggestions = json.loads(json_match.group())
                else:
                    suggestions = {"raw_response": response_text}
            except json.JSONDecodeError:
                suggestions = {"raw_response": response_text}
            
            # Sauvegarder les suggestions
            suggestions_path = LOGS_DIR / "suggestions" / f"suggestions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            suggestions_path.parent.mkdir(parents=True, exist_ok=True)
            suggestions_path.write_text(json.dumps(suggestions, indent=2, ensure_ascii=False))
            
            logger.info(f"Suggestions générées: {len(suggestions.get('suggestions', []))} items")
            
            return {
                "success": True,
                "suggestions": suggestions,
                "model_used": self.model,
                "report_path": str(suggestions_path)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # === Méthodes utilitaires ===
    
    def get_analysis_history(self, limit: int = 10) -> Dict[str, Any]:
        """Récupérer l'historique des analyses"""
        return {
            "success": True,
            "history": self.analysis_history[-limit:],
            "total": len(self.analysis_history)
        }
    
    def test_ollama_connection(self) -> Dict[str, Any]:
        """Tester la connexion à Ollama"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            
            if response.status_code == 200:
                models = response.json().get("models", [])
                return {
                    "success": True,
                    "connected": True,
                    "host": self.ollama_host,
                    "models": [m["name"] for m in models],
                    "configured_model": self.model
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "host": self.ollama_host
            }


# Instance singleton
self_improve_tools = SelfImproveTools()
