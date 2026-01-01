#!/usr/bin/env python3
"""
Tests unitaires pour le module de sécurité
"""

import os
import sys

import pytest

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security import (
    PathNotAllowedError,
    check_dangerous_patterns,
    extract_base_command,
    is_path_allowed,
    validate_command,
    validate_path,
)


class TestCommandValidation:
    """Tests pour la validation des commandes"""

    def test_allowed_simple_commands(self):
        """Les commandes simples doivent être autorisées"""
        commands = [
            "ls -la",
            "grep 'pattern' file.txt",
            "cat /etc/hosts",
            "docker ps",
            "git status",
            "systemctl status nginx",
        ]
        for cmd in commands:
            allowed, reason = validate_command(cmd)
            assert allowed, f"Command should be allowed: {cmd} (Reason: {reason})"

    def test_blocked_commands(self):
        """Les commandes dangereuses (blacklist) doivent être bloquées"""
        blocked_commands = [
            "mkfs /dev/sda",
            "fdisk -l",
            "dd if=/dev/zero of=/dev/sda",
            "rm -rf /",  # Pattern dangereux
        ]
        for cmd in blocked_commands:
            allowed, reason = validate_command(cmd)
            assert not allowed, f"Command should be blocked: {cmd}"

    def test_unknown_command_blocked(self):
        """
        En mode AUTONOME, les commandes inconnues SONT autorisées
        sauf si elles sont dans la blacklist.
        """
        cmd = "unknown_command --arg value"
        allowed, reason = validate_command(cmd)
        # En mode v5.1 autonome, c'est autorisé si pas blacklisté
        assert allowed, f"Unknown command should be allowed in autonomous mode: {cmd}"

    def test_empty_command(self):
        """Une commande vide doit être refusée"""
        allowed, reason = validate_command("")
        assert not allowed
        assert "vide" in reason

    def test_command_injection_patterns(self):
        """Les tentatives d'injection doivent être détectées (si patterns interdits)"""
        # Note: validate_command de base ne check pas forcément le shell complex
        # Mais on a des patterns interdits spécifiques
        injections = [
            "rm -rf /",
            "ls; rm -rf /",  # Pattern rm -rf /
        ]
        for cmd in injections:
            allowed, reason = validate_command(cmd)
            assert not allowed, f"Injection should be blocked: {cmd}"

    def test_extract_base_command(self):
        """Extraction de la commande de base"""
        cases = [
            ("ls -la", "ls"),
            ("docker ps", "docker"),
            ("/usr/bin/python3 script.py", "python3"),
            ("VAR=val cmd arg", "cmd"),
            ("grep pattern | sort", "grep"),
        ]
        for cmd, expected in cases:
            base = extract_base_command(cmd)
            assert base == expected


class TestPathValidation:
    """Tests pour la validation des chemins"""

    def test_allowed_read_paths(self):
        """Chemins autorisés en lecture"""
        paths = [
            "/data/file.txt",
            "/tmp/temp_file",
            "/var/log/syslog",
            "/etc/hosts",
        ]
        for path in paths:
            allowed, reason = is_path_allowed(path, write=False)
            assert allowed, f"Read path should be allowed: {path} (Reason: {reason})"

    def test_blocked_read_paths(self):
        """Chemins interdits en lecture"""
        paths = [
            "/etc/shadow",
            "/root/.ssh/id_rsa",
            "/.env",
            "/home/lalpha/.ssh/id_ed25519",
        ]
        for path in paths:
            allowed, reason = is_path_allowed(path, write=False)
            assert not allowed, f"Read path should be blocked: {path}"

    def test_allowed_write_paths(self):
        """Chemins autorisés en écriture"""
        paths = [
            "/data/output.json",
            "/tmp/test.log",
            "/home/lalpha/projets/new_file.py",
        ]
        for path in paths:
            allowed, reason = is_path_allowed(path, write=True)
            assert allowed, f"Write path should be allowed: {path} (Reason: {reason})"

    def test_blocked_write_paths(self):
        """Chemins interdits en écriture"""
        paths = [
            "/etc/hosts",  # Read-only
            "/bin/ls",
            "/usr/lib/python3",
            "/root/script.sh",
        ]
        for path in paths:
            allowed, reason = is_path_allowed(path, write=True)
            assert not allowed, f"Write path should be blocked: {path}"

    def test_path_traversal_blocked(self):
        """Traversée de répertoire interdite"""
        paths = [
            "/data/../etc/passwd",
            "/tmp/../../root/secret",
        ]
        for path in paths:
            # sanitize_path lève une exception
            with pytest.raises(PathNotAllowedError):
                validate_path(path)


class TestDangerousPatterns:
    """Tests des patterns regex dangereux"""

    def test_dangerous_patterns_detected(self):
        patterns = [
            "rm -rf /",
            "rm -rf /*",
            "cat /dev/zero > /dev/sda",
        ]
        for cmd in patterns:
            detected = check_dangerous_patterns(cmd)
            assert detected is not None, f"Should detect dangerous pattern in: {cmd}"

    def test_safe_patterns_not_flagged(self):
        safe_cmds = [
            "rm -rf /tmp/junk",  # Pas root
            "ls -la /",
            "echo 'hello' > file.txt",
        ]
        for cmd in safe_cmds:
            detected = check_dangerous_patterns(cmd)
            assert detected is None, f"Should NOT detect dangerous pattern in: {cmd}"


class TestExceptions:
    """Tests des exceptions spécifiques"""

    def test_path_not_allowed_error(self):
        with pytest.raises(PathNotAllowedError):
            validate_path("/etc/shadow")

    def test_performance(self):
        """Vérifier que la validation est rapide"""
        import time

        start = time.time()
        for _ in range(1000):
            validate_command("ls -la")
        duration = time.time() - start
        assert duration < 1.0, "Validation should be fast (>1000 ops/sec)"
