import asyncio
import logging
import uuid
import shutil
import os
from datetime import datetime
import subprocess
from engine import react_loop
from tools import execute_tool
from config import get_settings

logger = logging.getLogger("self_healing")

class SelfHealingService:
    def __init__(self):
        self.running = False
        self.check_interval = 300  # 5 minutes
        self.settings = get_settings()

    async def start(self):
        """Démarrer la boucle de surveillance"""
        self.running = True
        logger.info("🛡️ Self-Healing Service démarré")
        while self.running:
            try:
                await self.check_system_health()
            except Exception as e:
                logger.error(f"Erreur boucle self-healing: {e}")
            
            await asyncio.sleep(self.check_interval)

    def stop(self):
        self.running = False
        logger.info("🛑 Self-Healing Service arrêté")

    async def check_system_health(self):
        """Vérifier les métriques critiques"""
        issues = []

        # 1. Vérifier Espace Disque
        total, used, free = shutil.disk_usage("/")
        percent_used = (used / total) * 100
        if percent_used > 90:
            issues.append(f"⚠️ Espace disque CRITIQUE: {percent_used:.1f}% utilisé. Nettoie les logs ou fichiers temporaires.")

        # 2. Vérifier Docker (si disponible)
        try:
            res = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True)
            if res.returncode != 0:
                issues.append("⚠️ Docker semble inaccessible ou arrêté.")
        except Exception:
            pass # Docker peut ne pas être installé

        # 3. Vérifier Charge Système
        load = os.getloadavg()
        if load[0] > 4.0: # Arbitraire, dépend du CPU
            issues.append(f"⚠️ Charge système élevée (1 min): {load[0]}")

        # Si problèmes détectés, déclencher l'auto-réparation
        if issues:
            await self.trigger_healing(issues)

    async def trigger_healing(self, issues: list):
        """Lancer l'agent pour corriger les problèmes"""
        issue_text = "\n".join(issues)
        logger.warning(f"🚨 Problèmes détectés, lancement auto-réparation:\n{issue_text}")
        
        prompt = f"""ALERTE SYSTÈME (SELF-HEALING):
Les problèmes suivants ont été détectés automatiquement :
{issue_text}

Ta mission :
1. Analyse la cause (utilise logs_view, system_info, etc.)
2. Tente de corriger le problème (docker restart, suppression fichiers tmp, etc.)
3. Confirme que le système est stable.

Agis de manière autonome et sécurisée."""

        conv_id = f"self-healing-{datetime.now().strftime('%Y%m%d-%H%M')}"
        
        # Lancer le moteur ReAct
        # Note: on utilise un modèle performant pour la maintenance
        try:
            await react_loop(
                user_message=prompt,
                model=self.settings.default_model or "qwen2.5-coder:32b-instruct-q4_K_M",
                conversation_id=conv_id,
                execute_tool_func=execute_tool
            )
            logger.info(f"✅ Auto-réparation terminée (Conv ID: {conv_id})")
        except Exception as e:
            logger.error(f"❌ Échec de l'auto-réparation: {e}")

# Instance globale
service = SelfHealingService()
