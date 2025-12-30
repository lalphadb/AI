#!/usr/bin/env python3
"""
Script de test unitaire pour tous les outils de l'AI Orchestrator v5.0
"""

import asyncio
import json
import time
import pytest
from datetime import datetime

# Liste des paramètres pour les tests
test_params = [
    # ========== OUTILS SYSTÈME ==========
    ("system_info", {}, ["cpu", "memory"], False),
    ("disk_usage", {}, ["utilisation", "disponible"], False),
    ("disk_usage", {"path": "/tmp"}, ["tmp"], False),
    ("process_list", {}, ["pid"], False),
    ("execute_command", {"command": "echo 'test123'"}, ["test123"], False),
    ("execute_command", {"command": "whoami"}, [], False),
    ("service_status", {"service": "docker"}, [], False),
    ("logs_view", {"path": "/var/log/syslog", "lines": "5"}, [], False),

    # ========== OUTILS DOCKER ==========
    ("docker_status", {}, ["container", "status"], False),
    ("docker_stats", {}, [], False),
    ("docker_logs", {"container": "ai-orchestrator-backend", "lines": "5"}, [], False),

    # ========== OUTILS FICHIERS ==========
    ("read_file", {"path": "/etc/hostname"}, [], False),
    ("read_file", {"path": "/nonexistent/file"}, [], True),
    ("list_directory", {"path": "/app"}, ["main.py", "tools"], False),
    ("list_directory", {"path": "/app", "recursive": True}, [], False),
    ("search_files", {"pattern": "*.py", "path": "/app"}, [".py"], False),
    ("file_info", {"path": "/app/main.py"}, ["file"], False),
    
    # Test write_file avec validation syntaxe
    ("write_file", {"path": "/tmp/test_valid.py", "content": "def hello():\n    return 'world'"}, ["écrit"], False),
    ("write_file", {"path": "/tmp/test_invalid.py", "content": "def broken(\n    return"}, [], True),

    # ========== OUTILS GIT ==========
    ("git_status", {"path": "/home/lalpha/projets/ai-tools/ai-orchestrator"}, [], False),
    ("git_log", {"path": "/home/lalpha/projets/ai-tools/ai-orchestrator", "count": "3"}, [], False),
    ("git_branch", {"path": "/home/lalpha/projets/ai-tools/ai-orchestrator"}, [], False),

    # ========== OUTILS RÉSEAU ==========
    ("network_interfaces", {}, ["interface"], False),
    ("check_url", {"url": "https://google.com"}, ["200", "ok"], False),
    ("ping_host", {"host": "8.8.8.8"}, [], False),
    ("dns_lookup", {"domain": "google.com"}, [], False),

    # ========== OUTILS MÉMOIRE ==========
    ("memory_store", {"key": "test_key_123", "value": "Test value for unit testing", "category": "test"}, ["stocké", "mémorisé"], False),
    ("memory_recall", {"query": "test", "limit": "5"}, [], False),
    ("memory_list", {"category": "test"}, [], False),
    ("memory_delete", {"key": "test_key_123"}, [], False),

    # ========== OUTILS IA ==========
    ("final_answer", {"answer": "Ceci est une réponse de test"}, ["réponse", "test"], False),
    ("create_plan", {"objective": "Tester le système"}, [], False),

    # ========== META-OUTILS ==========
    ("list_my_tools", {}, ["outils", "disponibles"], False),
    ("reload_my_tools", {}, ["rechargés"], False),
    ("view_tool_code", {"name": "docker_status"}, ["register_tool", "docker"], False),
]

@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name, params, expected_contains, should_fail", test_params)
async def test_tool(tool_name: str, params: dict, expected_contains: list, should_fail: bool):
    """Tester un outil et vérifier le résultat"""
    from tools import execute_tool

    print(f"Testing tool: {tool_name}")
    
    start = time.time()
    try:
        result = await execute_tool(tool_name, params)
    except Exception as e:
        if should_fail:
             assert True
             return
        else:
             pytest.fail(f"Tool execution failed unexpectedly: {e}")

    elapsed = round((time.time() - start) * 1000, 2)

    # Vérifier si c'est une erreur
    is_error = result.startswith("❌") or "Erreur" in result

    if should_fail:
        assert is_error, f"Tool {tool_name} should have failed but succeeded. Result: {result}"
    else:
        assert not is_error, f"Tool {tool_name} failed. Result: {result}"
        if expected_contains:
            all_found = all(exp.lower() in result.lower() for exp in expected_contains)
            assert all_found, f"Expected content {expected_contains} not found in result: {result}"