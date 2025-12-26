#!/usr/bin/env python3
"""
Module de Sécurité pour AI Orchestrator v3.0
Validation des commandes, chemins, et protection contre les injections
"""

import os
import re
import shlex
from pathlib import Path
from typing import List, Tuple, Optional
from functools import wraps
from datetime import datetime
import logging

# Configuration du logging de sécurité
logging.basicConfig(level=logging.INFO)
security_logger = logging.getLogger("security")

# ===== CONFIGURATION DE SÉCURITÉ =====

# Commandes autorisées (whitelist)
ALLOWED_COMMANDS = {
    # Système
    "ls", "cat", "head", "tail", "grep", "find", "wc", "du", "df",
    "uptime", "hostname", "whoami", "pwd", "date", "uname",
    "free", "top", "ps", "lscpu", "lsblk", "ip", "ss", "netstat",

    # Docker
    "docker",

    # Git
    "git",

    # Services
    "systemctl", "journalctl",

    # Réseau
    "curl", "wget", "ping", "nslookup", "dig",

    # Fichiers
    "mkdir", "touch", "cp", "mv", "rm", "chmod", "chown",

    # Python/Node
    "python", "python3", "pip", "pip3", "node", "npm", "npx",

    # SSH (pour UDM)
    "ssh",

    # Utilitaires
    "echo", "printf", "test", "true", "false", "sleep",
    "tar", "gzip", "gunzip", "zip", "unzip",
    "sort", "uniq", "cut", "awk", "sed",
}

# Sous-commandes Docker autorisées
ALLOWED_DOCKER_SUBCOMMANDS = {
    "ps", "logs", "inspect", "stats", "top", "port",
    "images", "volume", "network",
    "start", "stop", "restart", "pause", "unpause",
    "exec",  # Limité par DOCKER_EXEC_WHITELIST
    "compose",
}

# Containers autorisés pour docker exec
DOCKER_EXEC_WHITELIST = {
    "ai-orchestrator-backend",
    "ai-orchestrator-frontend",
    "chromadb",
    "traefik",
    "prometheus",
    "grafana",
}

# Sous-commandes Git autorisées
ALLOWED_GIT_SUBCOMMANDS = {
    "status", "log", "diff", "branch", "checkout", "pull", "push",
    "add", "commit", "stash", "merge", "rebase", "fetch", "remote",
    "show", "blame", "tag", "describe",
}

# Sous-commandes systemctl autorisées
ALLOWED_SYSTEMCTL_SUBCOMMANDS = {
    "status", "start", "stop", "restart", "reload", "enable", "disable",
    "is-active", "is-enabled", "list-units", "list-unit-files",
}

# Services systemctl autorisés
ALLOWED_SERVICES = {
    "ollama", "docker", "nginx", "ssh", "cron",
    "prometheus", "grafana", "node_exporter",
}

# Chemins autorisés (lecture)
ALLOWED_READ_PATHS = [
    "/home/lalpha/projets",
    "/home/lalpha/documentation",
    "/home/lalpha/scripts",
    "/data",
    "/tmp",
    "/var/log",
    "/etc/hosts",
    "/etc/hostname",
    "/proc/loadavg",
    "/proc/meminfo",
    "/proc/cpuinfo",
]

# Chemins autorisés (écriture)
ALLOWED_WRITE_PATHS = [
    "/home/lalpha/projets",
    "/home/lalpha/scripts",
    "/data",
    "/tmp",
]

# Chemins interdits (blacklist absolue)
FORBIDDEN_PATHS = [
    "/etc/passwd",
    "/etc/shadow",
    "/etc/sudoers",
    "/root",
    "/.ssh",
    "/home/lalpha/.ssh",
    "/home/lalpha/.gnupg",
    "/home/lalpha/.bash_history",
    "/home/lalpha/.secrets",
    ".env",
    "credentials",
    "secret",
    "password",
    "token",
    "private_key",
    "id_rsa",
    "id_ed25519",
]

# Patterns dangereux dans les commandes
DANGEROUS_PATTERNS = [
    r";\s*rm\s+-rf",           # rm -rf après ;
    r"\|\s*sh",                 # pipe vers shell
    r"\|\s*bash",               # pipe vers bash
    r"`.*`",                    # command substitution backticks
    r"\$\(.*\)",                # command substitution $()
    r">\s*/etc/",               # redirection vers /etc
    r">\s*/root",               # redirection vers /root
    r"curl.*\|\s*sh",           # curl pipe shell
    r"wget.*\|\s*sh",           # wget pipe shell
    r"eval\s+",                 # eval
    r"exec\s+",                 # exec (sauf docker exec)
    r"sudo\s+",                 # sudo
    r"su\s+",                   # su
    r"chmod\s+777",             # chmod 777
    r"chmod\s+\+s",             # setuid
    r"mkfifo",                  # named pipes
    r"/dev/tcp",                # bash tcp
    r"/dev/udp",                # bash udp
    r"nc\s+-[el]",              # netcat listen
    r"ncat\s+-[el]",            # ncat listen
    r"socat",                   # socat
    r"python.*-c\s+['\"].*import\s+os", # python os import inline
]

# ===== CLASSES D'EXCEPTION =====

class SecurityError(Exception):
    """Exception de sécurité"""
    pass

class CommandNotAllowedError(SecurityError):
    """Commande non autorisée"""
    pass

class PathNotAllowedError(SecurityError):
    """Chemin non autorisé"""
    pass

class DangerousPatternError(SecurityError):
    """Pattern dangereux détecté"""
    pass

# ===== FONCTIONS DE VALIDATION =====

def sanitize_path(path: str) -> str:
    """
    Nettoyer et normaliser un chemin
    """
    # Résoudre le chemin absolu
    try:
        resolved = str(Path(path).resolve())
    except Exception:
        raise PathNotAllowedError(f"Chemin invalide: {path}")

    # Vérifier les traversées de répertoire
    if ".." in path:
        raise PathNotAllowedError(f"Traversée de répertoire interdite: {path}")

    return resolved

def is_path_allowed(path: str, write: bool = False) -> Tuple[bool, str]:
    """
    Vérifier si un chemin est autorisé

    Returns:
        (autorisé, raison)
    """
    try:
        resolved = sanitize_path(path)
    except PathNotAllowedError as e:
        return False, str(e)

    # Vérifier les chemins interdits
    for forbidden in FORBIDDEN_PATHS:
        if forbidden in resolved.lower():
            security_logger.warning(f"Tentative d'accès à un chemin interdit: {path}")
            return False, f"Chemin interdit: contient '{forbidden}'"

    # Vérifier les chemins autorisés
    allowed_paths = ALLOWED_WRITE_PATHS if write else ALLOWED_READ_PATHS

    for allowed in allowed_paths:
        if resolved.startswith(allowed):
            return True, "OK"

    action = "écriture" if write else "lecture"
    return False, f"Chemin non autorisé pour {action}: {resolved}"

def validate_path(path: str, write: bool = False) -> str:
    """
    Valider un chemin et lever une exception si non autorisé
    """
    allowed, reason = is_path_allowed(path, write)
    if not allowed:
        raise PathNotAllowedError(reason)
    return sanitize_path(path)

def extract_base_command(command: str) -> str:
    """
    Extraire la commande de base d'une ligne de commande
    """
    # Gérer les pipes et redirections
    cmd = command.split("|")[0].split(">")[0].split("<")[0].strip()

    # Gérer les variables d'environnement en préfixe
    while "=" in cmd.split()[0] if cmd.split() else False:
        parts = cmd.split(maxsplit=1)
        if len(parts) > 1:
            cmd = parts[1]
        else:
            break

    # Extraire le premier mot
    try:
        parts = shlex.split(cmd)
        if parts:
            return parts[0].split("/")[-1]  # Gérer /usr/bin/cmd
    except ValueError:
        # Si shlex échoue, utiliser split simple
        parts = cmd.split()
        if parts:
            return parts[0].split("/")[-1]

    return ""

def check_dangerous_patterns(command: str) -> Optional[str]:
    """
    Vérifier les patterns dangereux dans une commande

    Returns:
        Pattern trouvé ou None
    """
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return pattern
    return None

def validate_docker_command(command: str) -> Tuple[bool, str]:
    """
    Valider une commande Docker
    """
    parts = command.split()
    if len(parts) < 2:
        return False, "Commande docker incomplète"

    subcommand = parts[1]

    if subcommand not in ALLOWED_DOCKER_SUBCOMMANDS:
        return False, f"Sous-commande docker '{subcommand}' non autorisée"

    # Vérification spéciale pour docker exec
    if subcommand == "exec":
        # Trouver le nom du container
        container = None
        for i, part in enumerate(parts[2:], 2):
            if not part.startswith("-"):
                container = part
                break

        if container and container not in DOCKER_EXEC_WHITELIST:
            return False, f"Container '{container}' non autorisé pour docker exec"

    return True, "OK"

def validate_git_command(command: str) -> Tuple[bool, str]:
    """
    Valider une commande Git
    """
    parts = command.split()
    if len(parts) < 2:
        return False, "Commande git incomplète"

    subcommand = parts[1]

    if subcommand not in ALLOWED_GIT_SUBCOMMANDS:
        return False, f"Sous-commande git '{subcommand}' non autorisée"

    return True, "OK"

def validate_systemctl_command(command: str) -> Tuple[bool, str]:
    """
    Valider une commande systemctl
    """
    parts = command.split()
    if len(parts) < 2:
        return False, "Commande systemctl incomplète"

    subcommand = parts[1]

    if subcommand not in ALLOWED_SYSTEMCTL_SUBCOMMANDS:
        return False, f"Sous-commande systemctl '{subcommand}' non autorisée"

    # Vérifier le service si spécifié
    if len(parts) >= 3 and subcommand in {"start", "stop", "restart", "reload", "enable", "disable"}:
        service = parts[2].replace(".service", "")
        if service not in ALLOWED_SERVICES:
            return False, f"Service '{service}' non autorisé"

    return True, "OK"

def validate_command(command: str) -> Tuple[bool, str]:
    """
    Valider une commande complète

    Returns:
        (autorisé, raison)
    """
    if not command or not command.strip():
        return False, "Commande vide"

    command = command.strip()

    # Vérifier les patterns dangereux
    dangerous = check_dangerous_patterns(command)
    if dangerous:
        security_logger.warning(f"Pattern dangereux détecté: {dangerous} dans '{command}'")
        return False, f"Pattern dangereux détecté: {dangerous}"

    # Extraire et vérifier la commande de base
    base_cmd = extract_base_command(command)

    if not base_cmd:
        return False, "Impossible d'extraire la commande de base"

    if base_cmd not in ALLOWED_COMMANDS:
        security_logger.warning(f"Commande non autorisée: {base_cmd}")
        return False, f"Commande '{base_cmd}' non autorisée"

    # Validations spécifiques
    if base_cmd == "docker":
        return validate_docker_command(command)

    if base_cmd == "git":
        return validate_git_command(command)

    if base_cmd == "systemctl":
        return validate_systemctl_command(command)

    # Vérifier les chemins dans la commande pour rm
    if base_cmd == "rm":
        # Interdire rm -rf sur des chemins critiques
        if "-rf" in command or "-r" in command:
            for forbidden in ["/", "/home", "/etc", "/var", "/usr", "/root"]:
                if f" {forbidden}" in command or command.endswith(forbidden):
                    return False, f"Suppression récursive interdite sur {forbidden}"

    return True, "OK"

def secure_command(command: str) -> str:
    """
    Valider une commande et lever une exception si non autorisée
    """
    allowed, reason = validate_command(command)
    if not allowed:
        raise CommandNotAllowedError(reason)
    return command

# ===== AUDIT LOGGING =====

class AuditLog:
    """
    Journalisation des actions pour audit de sécurité
    """

    def __init__(self, log_file: str = "/data/audit.log"):
        self.log_file = log_file
        self.logger = logging.getLogger("audit")

        # Créer le handler de fichier si possible
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            handler = logging.FileHandler(log_file)
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        except Exception as e:
            print(f"Warning: Could not setup audit log file: {e}")

    def log_command(self, command: str, user: str = "anonymous",
                    allowed: bool = True, reason: str = ""):
        """Log une tentative d'exécution de commande"""
        status = "ALLOWED" if allowed else "BLOCKED"
        self.logger.info(f"COMMAND|{status}|user={user}|cmd={command[:200]}|reason={reason}")

    def log_file_access(self, path: str, action: str, user: str = "anonymous",
                        allowed: bool = True, reason: str = ""):
        """Log une tentative d'accès fichier"""
        status = "ALLOWED" if allowed else "BLOCKED"
        self.logger.info(f"FILE|{status}|user={user}|action={action}|path={path}|reason={reason}")

    def log_auth(self, user: str, success: bool, ip: str = ""):
        """Log une tentative d'authentification"""
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"AUTH|{status}|user={user}|ip={ip}")

    def log_security_event(self, event_type: str, details: str, severity: str = "WARNING"):
        """Log un événement de sécurité"""
        self.logger.log(
            getattr(logging, severity.upper(), logging.WARNING),
            f"SECURITY|{event_type}|{details}"
        )

# Instance globale d'audit
audit_log = AuditLog()

# ===== DÉCORATEURS =====

def require_safe_command(func):
    """Décorateur pour valider les commandes avant exécution"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        command = kwargs.get("command") or (args[0] if args else "")
        allowed, reason = validate_command(command)
        audit_log.log_command(command, allowed=allowed, reason=reason)
        if not allowed:
            raise CommandNotAllowedError(reason)
        return await func(*args, **kwargs)
    return wrapper

def require_safe_path(write: bool = False):
    """Décorateur pour valider les chemins"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            path = kwargs.get("path") or (args[0] if args else "")
            allowed, reason = is_path_allowed(path, write=write)
            audit_log.log_file_access(path, "write" if write else "read",
                                      allowed=allowed, reason=reason)
            if not allowed:
                raise PathNotAllowedError(reason)
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# ===== UTILITAIRES =====

def get_security_config() -> dict:
    """Retourner la configuration de sécurité actuelle"""
    return {
        "allowed_commands": list(ALLOWED_COMMANDS),
        "allowed_read_paths": ALLOWED_READ_PATHS,
        "allowed_write_paths": ALLOWED_WRITE_PATHS,
        "forbidden_paths": FORBIDDEN_PATHS,
        "docker_exec_whitelist": list(DOCKER_EXEC_WHITELIST),
        "allowed_services": list(ALLOWED_SERVICES),
    }

def add_allowed_path(path: str, write: bool = False):
    """Ajouter un chemin autorisé dynamiquement"""
    if write:
        if path not in ALLOWED_WRITE_PATHS:
            ALLOWED_WRITE_PATHS.append(path)
    else:
        if path not in ALLOWED_READ_PATHS:
            ALLOWED_READ_PATHS.append(path)

def add_allowed_command(command: str):
    """Ajouter une commande autorisée dynamiquement"""
    ALLOWED_COMMANDS.add(command)
