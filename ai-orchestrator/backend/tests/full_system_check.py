#!/usr/bin/env python3
"""
Test Complet du Système AI Orchestrator
Vérifie: Autonomie, Outils, Mémoire, Sécurité
"""

import sys
import os
import asyncio
import logging
from unittest.mock import MagicMock, patch

# Setup path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import execute_tool, get_tools_description
from engine import react_loop
from auto_learn import auto_learn_from_message

# Logger pour le test
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("TEST")

class MockLLMResponse:
    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0

    def json(self):
        resp = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return {"message": {"content": resp}}

async def test_tools_execution():
    logger.info("\n=== 1. TEST DES OUTILS SYSTÈME (Réel) ===")
    
    # Test disk_usage
    logger.info(">> Test disk_usage('/')")
    res = await execute_tool("disk_usage", {"path": "/"})
    if "Espace disque" in res and "%" in res:
        logger.info("✅ disk_usage: SUCCÈS")
    else:
        logger.error(f"❌ disk_usage: ÉCHEC\n{res}")

    # Test protection injection
    logger.info(">> Test Injection: execute_command('echo safe; whoami')")
    res = await execute_tool("execute_command", {"command": "echo safe; whoami"})
    if ";" in res and "safe" in res: 
        logger.info("✅ Protection Injection: SUCCÈS (Le point-virgule est traité comme texte)")
    else:
        logger.error(f"❌ Protection Injection: ÉCHEC\n{res}")

async def test_memory_learning():
    logger.info("\n=== 2. TEST AUTO-APPRENTISSAGE (Simulation) ===")
    
    msg = "Je travaille sur le projet SecretBase avec Python."
    conv_id = "test_conv_123"
    
    # On mock ChromaDB pour ne pas polluer la vraie DB
    with patch('auto_learn.get_chroma_collection') as mock_db:
        mock_collection = MagicMock()
        mock_db.return_value = mock_collection
        
        logger.info(f"Message utilisateur: '{msg}'")
        learned = auto_learn_from_message(msg, conv_id)
        
        # Vérifier si des faits ont été extraits
        found_project = any("SecretBase" in f for f in learned)
        if found_project:
            logger.info(f"✅ Fait appris: {learned}")
            logger.info("✅ Auto-Learn a détecté le projet.")
        else:
            logger.error(f"❌ Auto-Learn n'a rien détecté. Résultat: {learned}")

async def test_react_engine_logic():
    logger.info("\n=== 3. TEST DU MOTEUR REACT (Simulation) ===")
    
    # Scénario : L'IA doit vérifier le disque et répondre
    fake_responses = [
        # Tour 1: Réflexion + Action
        """THINK: L'utilisateur veut vérifier l'espace disque. Je vais utiliser l'outil approprié.
ACTION: disk_usage(path=\"/\")""",
        
        # Tour 2: Analyse résultat + Réponse finale
        """THINK: J'ai reçu les infos du disque. Tout semble normal.
ACTION: final_answer(answer=\"L'espace disque est suffisant.\")"""
    ]
    
    # On mock httpx pour simuler Ollama
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.return_value = MockLLMResponse(fake_responses)
        
        logger.info(">> Lancement boucle ReAct (Mocked LLM)")
        result = await react_loop(
            user_message="Vérifie mon disque",
            model="test-model",
            conversation_id="test-1",
            execute_tool_func=execute_tool
        )
        
        if "L'espace disque est suffisant" in result:
            logger.info("✅ Moteur ReAct: SUCCÈS (Cycle Think -> Act -> Final)")
        else:
            logger.error(f"❌ Moteur ReAct: ÉCHEC. Résultat: {result}")

async def run_all_tests():
    logger.info("🚀 DÉMARRAGE DU CHECKUP COMPLET DU SYSTÈME")
    await test_tools_execution()
    await test_memory_learning()
    await test_react_engine_logic()
    logger.info("\n🏁 CHECKUP TERMINÉ")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
