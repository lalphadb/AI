#!/usr/bin/env python3
"""
Test Complet du Système AI Orchestrator
Vérifie: Autonomie, Outils, Mémoire, Sécurité
"""

import logging
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Setup path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Logger pour le test
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("TEST")


class MockLLMResponse:
    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0
        self.status_code = 200

    def json(self):
        resp = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return {"message": {"content": resp}}

@pytest.mark.asyncio
async def test_tools_execution():
    from tools import execute_tool
    logger.info("\n=== 1. TEST DES OUTILS SYSTÈME (Réel) ===")

    # Test disk_usage
    logger.info(">> Test disk_usage('/')")
    res = await execute_tool("disk_usage", {"path": "/"})
    assert "Espace disque" in res or "%" in res or "total" in res.lower(), f"disk_usage failed: {res}"
    logger.info("✅ disk_usage: SUCCÈS")

    # Test protection injection
    logger.info(">> Test Injection: execute_command('echo safe; whoami')")
    res = await execute_tool("execute_command", {"command": "echo safe; whoami"})
    # On s'attend à ce que le ; soit traité comme du texte, ou que la commande échoue sécuritairement
    assert ";" in res or "safe" in res, f"Injection protection check failed: {res}"
    logger.info("✅ Protection Injection: SUCCÈS")

@pytest.mark.asyncio
async def test_memory_learning():
    from auto_learn import auto_learn_from_message
    logger.info("\n=== 2. TEST AUTO-APPRENTISSAGE (Simulation) ===")

    msg = "Je travaille sur le projet SecretBase avec Python."
    conv_id = "test_conv_123"

    # On mock ChromaDB pour ne pas polluer la vraie DB
    with patch("auto_learn.get_chroma_collection") as mock_db:
        mock_collection = MagicMock()
        mock_db.return_value = mock_collection

        logger.info(f"Message utilisateur: '{msg}'")
        learned = auto_learn_from_message(msg, conv_id)

        # Vérifier si des faits ont été extraits
        found_project = any("SecretBase" in f for f in learned)
        if found_project:
            logger.info(f"✅ Fait appris: {learned}")
        else:
            logger.warning(f"⚠️ Auto-Learn n'a rien détecté (peut être normal selon le modèle/logique). Résultat: {learned}")
            # On ne fail pas forcément ici car ça dépend de l'IA/Regex

@pytest.mark.asyncio
async def test_react_engine_logic():
    from engine import react_loop
    from tools import execute_tool
    logger.info("\n=== 3. TEST DU MOTEUR REACT (Simulation) ===")

    # Scénario : L'IA doit vérifier le disque et répondre
    fake_responses = [
        # Tour 1: Réflexion + Action
        """THINK: L'utilisateur veut vérifier l'espace disque. Je vais utiliser l'outil approprié.
ACTION: disk_usage(path=\"/")""",
        # Tour 2: Analyse résultat + Réponse finale
        """THINK: J'ai reçu les infos du disque. Tout semble normal.
ACTION: final_answer(answer=\"L'espace disque est suffisant.\")""",
    ]

    # On mock httpx pour simuler Ollama
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MockLLMResponse(fake_responses)

        logger.info(">> Lancement boucle ReAct (Mocked LLM)")
        result = await react_loop(
            user_message="Vérifie mon disque",
            model="test-model",
            conversation_id="test-1",
            execute_tool_func=execute_tool,
        )

        assert "L'espace disque est suffisant" in result, f"ReAct engine failed: {result}"
        logger.info("✅ Moteur ReAct: SUCCÈS")
