#!/usr/bin/env python3
"""
Test du fonctionnement global - Questions complexes via ReAct
"""

import asyncio
import time

import pytest

questions = [
    # Question 1: État système simple
    "Quel est l'état actuel du système? Donne-moi les infos CPU, RAM et disque.",
    # Question 2: Docker multi-outils
    "Liste tous les conteneurs Docker et montre-moi les logs des 5 dernières lignes du conteneur backend.",
    # Question 3: Analyse fichier + Git
    "Lis le fichier /app/main.py et dis-moi combien de lignes il fait. Montre aussi le dernier commit git du projet.",
    # Question 4: Réseau
    "Vérifie si google.com est accessible et fais un ping vers 8.8.8.8. Donne-moi le temps de réponse.",
    # Question 5: Auto-amélioration
    "Crée un nouvel outil appelé 'hello_test' qui retourne 'Hello from auto-created tool!', puis teste-le immédiatement.",
]

@pytest.mark.asyncio
@pytest.mark.parametrize("question", questions)
async def test_react_question(question: str):
    """Tester une question via le moteur ReAct"""
    from engine import react_loop
    from tools import execute_tool

    print(f"\n{'=' * 60}")
    print(f"❓ QUESTION: {question[:80]}...")
    print(f"{'=' * 60}")

    start = time.time()
    timeout = 90

    try:
        response = await asyncio.wait_for(
            react_loop(
                user_message=question,
                model="qwen2.5-coder:32b-instruct-q4_K_M",  # Modèle local
                conversation_id=f"test-{int(time.time())}",
                execute_tool_func=execute_tool,
            ),
            timeout=timeout,
        )
        elapsed = round(time.time() - start, 2)

        print(f"\n✅ RÉPONSE ({elapsed}s):")
        print("-" * 40)
        # Afficher les 500 premiers caractères
        print(response[:500] if len(response) > 500 else response)
        if len(response) > 500:
            print(f"\n... ({len(response)} caractères au total)")

        # Simple assertion that we got a non-empty response
        assert response and len(response) > 0

    except TimeoutError:
        print(f"⏱️ TIMEOUT après {timeout}s")
        pytest.fail(f"Timeout after {timeout}s")
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        print(f"❌ ERREUR ({elapsed}s): {e}")
        pytest.fail(f"Error during React Loop: {e}")
