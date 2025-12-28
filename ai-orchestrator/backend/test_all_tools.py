#!/usr/bin/env python3
"""
Script de test unitaire pour tous les outils de l'AI Orchestrator v5.0
"""

import asyncio
import json
import time
from datetime import datetime

# Résultats des tests
RESULTS = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "errors": [],
    "details": []
}


async def test_tool(tool_name: str, params: dict, expected_contains: list = None, should_fail: bool = False):
    """Tester un outil et vérifier le résultat"""
    from tools import execute_tool

    RESULTS["total"] += 1
    start = time.time()

    try:
        result = await execute_tool(tool_name, params)
        elapsed = round((time.time() - start) * 1000, 2)

        # Vérifier si c'est une erreur
        is_error = result.startswith("❌") or "Erreur" in result

        if should_fail and is_error:
            status = "PASS"
            RESULTS["passed"] += 1
        elif not should_fail and not is_error:
            # Vérifier le contenu attendu
            if expected_contains:
                all_found = all(exp.lower() in result.lower() for exp in expected_contains)
                if all_found:
                    status = "PASS"
                    RESULTS["passed"] += 1
                else:
                    status = "FAIL"
                    RESULTS["failed"] += 1
                    RESULTS["errors"].append(f"{tool_name}: Contenu attendu non trouvé")
            else:
                status = "PASS"
                RESULTS["passed"] += 1
        else:
            status = "FAIL"
            RESULTS["failed"] += 1
            RESULTS["errors"].append(f"{tool_name}: {result[:100]}")

        RESULTS["details"].append({
            "tool": tool_name,
            "status": status,
            "time_ms": elapsed,
            "result_preview": result[:200] if len(result) > 200 else result
        })

        icon = "✅" if status == "PASS" else "❌"
        print(f"  {icon} {tool_name} ({elapsed}ms)")

        return status == "PASS"

    except Exception as e:
        RESULTS["failed"] += 1
        RESULTS["errors"].append(f"{tool_name}: Exception - {str(e)}")
        RESULTS["details"].append({
            "tool": tool_name,
            "status": "ERROR",
            "error": str(e)
        })
        print(f"  💥 {tool_name}: {e}")
        return False


async def run_all_tests():
    """Exécuter tous les tests"""

    print("=" * 60)
    print("🧪 TESTS UNITAIRES - AI Orchestrator v5.0")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # ========== OUTILS SYSTÈME ==========
    print("\n📦 SYSTÈME")
    await test_tool("system_info", {}, ["cpu", "memory"])
    await test_tool("disk_usage", {}, ["utilisation", "disponible"])
    await test_tool("disk_usage", {"path": "/tmp"}, ["tmp"])
    await test_tool("process_list", {}, ["pid"])
    await test_tool("execute_command", {"command": "echo 'test123'"}, ["test123"])
    await test_tool("execute_command", {"command": "whoami"})
    await test_tool("service_status", {"service": "docker"})
    await test_tool("logs_view", {"path": "/var/log/syslog", "lines": "5"})

    # ========== OUTILS DOCKER ==========
    print("\n🐳 DOCKER")
    await test_tool("docker_status", {}, ["container", "status"])
    await test_tool("docker_stats", {})
    await test_tool("docker_logs", {"container": "ai-orchestrator-backend", "lines": "5"})

    # ========== OUTILS FICHIERS ==========
    print("\n📁 FICHIERS")
    await test_tool("read_file", {"path": "/etc/hostname"})
    await test_tool("read_file", {"path": "/nonexistent/file"}, should_fail=True)
    await test_tool("list_directory", {"path": "/app"}, ["main.py", "tools"])
    await test_tool("list_directory", {"path": "/app", "recursive": True})
    await test_tool("search_files", {"pattern": "*.py", "path": "/app"}, [".py"])
    await test_tool("file_info", {"path": "/app/main.py"}, ["file"])

    # Test write_file avec validation syntaxe
    await test_tool("write_file", {
        "path": "/tmp/test_valid.py",
        "content": "def hello():\n    return 'world'"
    }, ["écrit"])

    await test_tool("write_file", {
        "path": "/tmp/test_invalid.py",
        "content": "def broken(\n    return"
    }, should_fail=True)

    # ========== OUTILS GIT ==========
    print("\n📚 GIT")
    await test_tool("git_status", {"path": "/home/lalpha/projets/ai-tools/ai-orchestrator"})
    await test_tool("git_log", {"path": "/home/lalpha/projets/ai-tools/ai-orchestrator", "count": "3"})
    await test_tool("git_branch", {"path": "/home/lalpha/projets/ai-tools/ai-orchestrator"})

    # ========== OUTILS RÉSEAU ==========
    print("\n🌐 RÉSEAU")
    await test_tool("network_interfaces", {}, ["interface"])
    await test_tool("check_url", {"url": "https://google.com"}, ["200", "ok"])
    await test_tool("ping_host", {"host": "8.8.8.8"})
    await test_tool("dns_lookup", {"domain": "google.com"})

    # ========== OUTILS MÉMOIRE ==========
    print("\n🧠 MÉMOIRE")
    await test_tool("memory_store", {
        "key": "test_key_123",
        "value": "Test value for unit testing",
        "category": "test"
    }, ["stocké", "mémorisé"])

    await test_tool("memory_recall", {"query": "test", "limit": "5"})
    await test_tool("memory_list", {"category": "test"})
    await test_tool("memory_delete", {"key": "test_key_123"})

    # ========== OUTILS IA ==========
    print("\n🤖 IA")
    await test_tool("final_answer", {"answer": "Ceci est une réponse de test"}, ["réponse", "test"])
    await test_tool("create_plan", {"objective": "Tester le système"})
    # summarize et web_search nécessitent un LLM, on les skip

    # ========== META-OUTILS ==========
    print("\n🔧 META-OUTILS")
    await test_tool("list_my_tools", {}, ["outils", "disponibles"])
    await test_tool("reload_my_tools", {}, ["rechargés"])
    await test_tool("view_tool_code", {"name": "docker_status"}, ["register_tool", "docker"])

    # Test création/suppression d'outil
    print("\n🆕 TEST AUTO-AMÉLIORATION")
    created = await test_tool("create_tool", {
        "name": "test_auto_tool",
        "description": "Outil de test automatique",
        "parameters": {"msg": "str"},
        "code": '''async def test_auto_tool(params: dict) -> str:
    msg = params.get("msg", "default")
    return f"Test OK: {msg}"'''
    }, ["créé", "succès"])

    if created:
        await test_tool("test_auto_tool", {"msg": "Hello"}, ["Test OK", "Hello"])
        await test_tool("delete_tool", {"name": "test_auto_tool"}, ["supprimé"])

    # ========== RÉSUMÉ ==========
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 60)
    print(f"Total:    {RESULTS['total']}")
    print(f"✅ Passés: {RESULTS['passed']}")
    print(f"❌ Échoués: {RESULTS['failed']}")
    print(f"⏭️  Skippés: {RESULTS['skipped']}")

    if RESULTS['errors']:
        print("\n⚠️ ERREURS:")
        for err in RESULTS['errors'][:10]:
            print(f"  - {err}")

    success_rate = (RESULTS['passed'] / RESULTS['total'] * 100) if RESULTS['total'] > 0 else 0
    print(f"\n📈 Taux de réussite: {success_rate:.1f}%")

    return RESULTS


if __name__ == "__main__":
    results = asyncio.run(run_all_tests())
    # Sauvegarder les résultats
    with open("/tmp/test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n💾 Résultats sauvegardés dans /tmp/test_results.json")
