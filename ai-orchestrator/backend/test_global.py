#!/usr/bin/env python3
"""
Test du fonctionnement global - Questions complexes via ReAct
"""

import asyncio
import time
from datetime import datetime


async def test_react_question(question: str, timeout: int = 60):
    """Tester une question via le moteur ReAct"""
    from engine import react_loop
    from tools import execute_tool

    print(f"\n{'='*60}")
    print(f"❓ QUESTION: {question[:80]}...")
    print(f"{'='*60}")

    start = time.time()

    try:
        response = await asyncio.wait_for(
            react_loop(
                user_message=question,
                model="qwen2.5-coder:32b-instruct-q4_K_M",  # Modèle local
                conversation_id=f"test-{int(time.time())}",
                execute_tool_func=execute_tool
            ),
            timeout=timeout
        )
        elapsed = round(time.time() - start, 2)

        print(f"\n✅ RÉPONSE ({elapsed}s):")
        print("-" * 40)
        # Afficher les 500 premiers caractères
        print(response[:500] if len(response) > 500 else response)
        if len(response) > 500:
            print(f"\n... ({len(response)} caractères au total)")

        return True, elapsed, response

    except asyncio.TimeoutError:
        print(f"⏱️ TIMEOUT après {timeout}s")
        return False, timeout, "Timeout"
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        print(f"❌ ERREUR ({elapsed}s): {e}")
        return False, elapsed, str(e)


async def run_global_tests():
    print("=" * 60)
    print("🌐 TEST FONCTIONNEMENT GLOBAL - AI Orchestrator v5.0")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

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

    results = []

    for i, q in enumerate(questions, 1):
        print(f"\n\n📝 TEST {i}/{len(questions)}")
        success, elapsed, response = await test_react_question(q, timeout=90)
        results.append({
            "question": q,
            "success": success,
            "time": elapsed,
            "response_length": len(response)
        })

        # Pause entre les tests
        await asyncio.sleep(2)

    # Résumé
    print("\n\n" + "=" * 60)
    print("📊 RÉSUMÉ TESTS GLOBAUX")
    print("=" * 60)

    passed = sum(1 for r in results if r["success"])
    total = len(results)
    avg_time = sum(r["time"] for r in results) / total if total > 0 else 0

    print(f"Tests réussis: {passed}/{total}")
    print(f"Temps moyen: {avg_time:.1f}s")

    for i, r in enumerate(results, 1):
        status = "✅" if r["success"] else "❌"
        print(f"  {status} Test {i}: {r['time']:.1f}s, {r['response_length']} chars")

    return results


if __name__ == "__main__":
    asyncio.run(run_global_tests())
