#!/usr/bin/env python3
"""
Script de test unitaire v2 pour AI Orchestrator v5.0
Critères de vérification corrigés
"""

import asyncio
import json
import time
from datetime import datetime

RESULTS = {"total": 0, "passed": 0, "failed": 0, "details": [], "errors": []}


async def test_tool(name: str, params: dict, must_not_fail: bool = True, check_fn=None):
    """Tester un outil"""
    from tools import execute_tool

    RESULTS["total"] += 1
    start = time.time()

    try:
        result = await execute_tool(name, params)
        elapsed = round((time.time() - start) * 1000, 2)

        is_error = "❌" in result or "Erreur" in result

        if must_not_fail and is_error:
            status = "FAIL"
            RESULTS["failed"] += 1
            RESULTS["errors"].append(f"{name}: {result[:100]}")
        elif not must_not_fail and is_error:
            status = "PASS"
            RESULTS["passed"] += 1
        elif check_fn and not check_fn(result):
            status = "FAIL"
            RESULTS["failed"] += 1
            RESULTS["errors"].append(f"{name}: Vérification échouée")
        else:
            status = "PASS"
            RESULTS["passed"] += 1

        RESULTS["details"].append({"tool": name, "status": status, "time_ms": elapsed})
        icon = "✅" if status == "PASS" else "❌"
        print(f"  {icon} {name} ({elapsed}ms)")
        return status == "PASS"

    except Exception as e:
        RESULTS["failed"] += 1
        RESULTS["errors"].append(f"{name}: {e}")
        print(f"  💥 {name}: {e}")
        return False


async def run_tests():
    print("=" * 60)
    print("🧪 TESTS UNITAIRES v2 - AI Orchestrator v5.0")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # ========== SYSTÈME ==========
    print("\n📦 SYSTÈME")
    await test_tool("system_info", {}, check_fn=lambda r: "RAM" in r or "CPU" in r)
    await test_tool("disk_usage", {}, check_fn=lambda r: "%" in r or "total" in r.lower())
    await test_tool("disk_usage", {"path": "/tmp"})
    await test_tool("process_list", {}, check_fn=lambda r: "PID" in r or "pid" in r.lower())
    await test_tool("execute_command", {"command": "echo TEST_OK"}, check_fn=lambda r: "TEST_OK" in r)
    await test_tool("execute_command", {"command": "whoami"})
    await test_tool("service_status", {"service": "docker"})
    await test_tool("logs_view", {"path": "/var/log/syslog", "lines": "3"})

    # ========== DOCKER ==========
    print("\n🐳 DOCKER")
    await test_tool("docker_status", {}, check_fn=lambda r: "NAMES" in r or "Container" in r)
    await test_tool("docker_stats", {}, check_fn=lambda r: "CPU" in r or "MEM" in r or "%" in r)
    await test_tool("docker_logs", {"container": "ai-orchestrator-backend", "lines": "3"})
    await test_tool("docker_exec", {"container": "ai-orchestrator-backend", "command": "echo DOCKER_EXEC_OK"},
                    check_fn=lambda r: "DOCKER_EXEC_OK" in r)

    # ========== FICHIERS ==========
    print("\n📁 FICHIERS")
    await test_tool("read_file", {"path": "/etc/hostname"})
    await test_tool("read_file", {"path": "/nonexistent"}, must_not_fail=False)
    await test_tool("list_directory", {"path": "/app"}, check_fn=lambda r: "main.py" in r)
    await test_tool("list_directory", {"path": "/app", "recursive": True})
    await test_tool("search_files", {"pattern": "*.py", "path": "/app"}, check_fn=lambda r: ".py" in r)
    await test_tool("file_info", {"path": "/app/main.py"})
    await test_tool("write_file", {"path": "/tmp/test_ok.py", "content": "print('ok')"},
                    check_fn=lambda r: "écrit" in r.lower() or "✅" in r)
    await test_tool("write_file", {"path": "/tmp/bad.py", "content": "def broken("}, must_not_fail=False)

    # ========== GIT ==========
    print("\n📚 GIT")
    await test_tool("git_status", {"path": "/home/lalpha/projets/ai-tools/ai-orchestrator"})
    await test_tool("git_log", {"path": "/home/lalpha/projets/ai-tools/ai-orchestrator", "count": "3"})
    await test_tool("git_branch", {"path": "/home/lalpha/projets/ai-tools/ai-orchestrator"})
    await test_tool("git_diff", {"path": "/home/lalpha/projets/ai-tools/ai-orchestrator"})

    # ========== RÉSEAU ==========
    print("\n🌐 RÉSEAU")
    await test_tool("network_interfaces", {}, check_fn=lambda r: "eth" in r.lower() or "lo" in r.lower())
    await test_tool("check_url", {"url": "https://google.com"}, check_fn=lambda r: "200" in r)
    await test_tool("ping_host", {"host": "8.8.8.8"}, check_fn=lambda r: "ms" in r.lower() or "time" in r.lower())
    await test_tool("dns_lookup", {"host": "google.com"}, check_fn=lambda r: "." in r and ("address" in r.lower() or "1" in r))

    # ========== MÉMOIRE ==========
    print("\n🧠 MÉMOIRE")
    await test_tool("memory_store", {"key": "unit_test_key", "value": "Unit test value", "category": "test"},
                    check_fn=lambda r: "mémorisé" in r.lower() or "✅" in r)
    await test_tool("memory_recall", {"query": "unit test", "limit": "5"})
    await test_tool("memory_list", {"category": "test"})
    await test_tool("memory_delete", {"key": "unit_test_key"})

    # ========== IA ==========
    print("\n🤖 IA")
    await test_tool("final_answer", {"answer": "Test réponse"})
    await test_tool("create_plan", {"objective": "Tester le système"})

    # ========== META-OUTILS ==========
    print("\n🔧 META-OUTILS")
    await test_tool("list_my_tools", {}, check_fn=lambda r: "outils" in r.lower())
    await test_tool("reload_my_tools", {}, check_fn=lambda r: "rechargé" in r.lower())
    await test_tool("view_tool_code", {"name": "docker_status"}, check_fn=lambda r: "python" in r.lower())

    # ========== AUTO-AMÉLIORATION ==========
    print("\n🆕 AUTO-AMÉLIORATION")
    await test_tool("create_tool", {
        "name": "unit_test_tool",
        "description": "Outil de test unitaire",
        "parameters": {"x": "str"},
        "code": '''async def unit_test_tool(params: dict) -> str:
    return f"UNIT_TEST_OK: {params.get('x', 'default')}"'''
    }, check_fn=lambda r: "créé" in r.lower() or "✅" in r)

    await test_tool("unit_test_tool", {"x": "hello"}, check_fn=lambda r: "UNIT_TEST_OK" in r)
    await test_tool("delete_tool", {"name": "unit_test_tool"}, check_fn=lambda r: "supprimé" in r.lower())

    # ========== UDM (peut échouer si pas configuré) ==========
    print("\n📡 UDM (optionnel)")
    await test_tool("udm_status", {})
    await test_tool("udm_clients", {})

    # ========== RÉSUMÉ ==========
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ")
    print("=" * 60)
    rate = (RESULTS["passed"] / RESULTS["total"] * 100) if RESULTS["total"] > 0 else 0
    print(f"Total: {RESULTS['total']} | ✅ {RESULTS['passed']} | ❌ {RESULTS['failed']}")
    print(f"📈 Taux de réussite: {rate:.1f}%")

    if RESULTS["errors"]:
        print("\n⚠️ Erreurs:")
        for e in RESULTS["errors"][:10]:
            print(f"  - {e[:80]}")

    return RESULTS


if __name__ == "__main__":
    results = asyncio.run(run_tests())
    with open("/tmp/test_results_v2.json", "w") as f:
        json.dump(results, f, indent=2)
