"""
Module de sécurité pour AI Orchestrator v5.2
Mode Autonome (blacklist commandes) + Validation chemins
SECURITE: Blacklist etendue (audit 2025-12-30)
"""

import logging
import os
import re
import shlex
from pathlib import Path

logger = logging.getLogger(__name__)

# MODE AUTONOME - Tout est permis sauf la blacklist
AUTONOMOUS_MODE = True

# Commandes INTERDITES (blacklist) - ETENDUE 2025-12-30
FORBIDDEN_COMMANDS = {
    # Formatage / Partitionnement
    "mkfs",
    "fdisk",
    "parted",
    "dd",
    # Modules kernel
    "insmod",
    "rmmod",
    "modprobe",
    # Telechargement (risque malware)
    "wget",
    "curl",  # Note: curl utilise via API est OK, mais pas en shell direct
    # Reverse shells / Reseau dangereux
    "nc",
    "netcat",
    "ncat",
    "socat",
    "telnet",
    # Modification permissions/proprietaires sensibles
    "chown",
    # Gestion utilisateurs (creation backdoors)
    "useradd",
    "usermod",
    "userdel",
    "groupadd",
    "passwd",
    "adduser",
    # Crontab (persistance)
    "crontab",
    # Interpreters (execution code arbitraire) - commentes car necessaires
    # "python", "python3", "perl", "ruby", "node",
    # SSH (mouvement lateral)
    "ssh-keygen",
    "ssh-copy-id",
    # Iptables (manipulation firewall)
    "iptables",
    "ip6tables",
    "nft",
    "ufw",
    # Montage filesystems
    "mount",
    "umount",
    # Arret systeme
    "shutdown",
    "reboot",
    "poweroff",
    "halt",
    "init",
}

# Patterns dangereux - ETENDUS
FORBIDDEN_PATTERNS = [
    r"rm\s+-rf\s+/\s*$",
    r"rm\s+-rf\s+/\*",
    r"rm\s+-rf\s+~",
    r"rm\s+-rf\s+\$HOME",
    r">\s*/dev/sd[a-z]",
    r">\s*/dev/nvme",
    r":(){ :|:& };:",  # Fork bomb
    r"/dev/tcp/",  # Bash reverse shell
    r"/dev/udp/",
    r"mkfifo",  # Named pipes (reverse shells)
    r"base64\s+-d.*\|.*sh",  # Obfuscated execution
    r"eval\s+.*base64",
    r"\|\s*sh\s*$",  # Pipe to shell
    r"\|\s*bash\s*$",
    r"chmod\s+[0-7]*777",  # World writable
    r"chmod\s+\+s",  # SUID bit
]

# Chemins interdits en écriture
FORBIDDEN_WRITE_PATHS = ["/boot", "/usr/bin", "/usr/sbin", "/bin", "/sbin", "/lib"]

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


# ===== FONCTIONS DE VALIDATION DE CHEMINS =====


def sanitize_path(path: str) -> str:
    """
    Nettoyer et normaliser un chemin
    SECURITE: Verification des symlinks (audit 2025-12-30)
    """
    if not path:
        raise PathNotAllowedError("Chemin vide")

    # Verifier traversee AVANT resolution
    if ".." in path:
        raise PathNotAllowedError(f"Traversée de répertoire interdite: {path}")

    try:
        path_obj = Path(path)
        resolved = str(path_obj.resolve())
    except Exception:
        raise PathNotAllowedError(f"Chemin invalide: {path}")

    # SECURITE: Verifier si c'est un symlink qui pointe hors des chemins autorises
    if path_obj.is_symlink():
        logger.warning(f"Symlink detecte: {path} -> {resolved}")
        # La verification sera faite dans is_path_allowed avec le chemin resolu

    return resolved


def is_path_allowed(path: str, write: bool = False) -> tuple[bool, str]:
    """
    Vérifier si un chemin est autorisé
    SECURITE: Verification du chemin RESOLU (pas le symlink source)

    Returns:
        (autorisé, raison)
    """
    try:
        resolved = sanitize_path(path)
    except PathNotAllowedError as e:
        return False, str(e)

    # Vérifier les chemins interdits SUR LE CHEMIN RESOLU
    for forbidden in FORBIDDEN_PATHS:
        if forbidden in resolved.lower():
            logger.warning(f"Tentative d'accès à un chemin interdit: {path} (resolu: {resolved})")
            return False, f"Chemin interdit: contient '{forbidden}'"

    # Vérifier les chemins autorisés SUR LE CHEMIN RESOLU
    allowed_paths = ALLOWED_WRITE_PATHS if write else ALLOWED_READ_PATHS

    path_allowed = False
    for allowed in allowed_paths:
        if resolved.startswith(allowed):
            path_allowed = True
            break

    if not path_allowed:
        action = "écriture" if write else "lecture"
        # SECURITE: Inclure le chemin resolu dans le message pour debug
        if path != resolved:
            return False, f"Chemin non autorisé pour {action}: {path} (symlink vers {resolved})"
        return False, f"Chemin non autorisé pour {action}: {resolved}"

    return True, "OK"


def validate_path(path: str, write: bool = False) -> str:
    """Valider un chemin et lever une exception si non autorisé"""
    allowed, reason = is_path_allowed(path, write)
    if not allowed:
        raise PathNotAllowedError(reason)
    return sanitize_path(path)


def check_dangerous_patterns(command: str) -> str | None:
    """Vérifier les patterns dangereux dans une commande"""
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return pattern
    return None


def extract_base_command(command: str) -> str:
    """Extraire la commande de base d'une ligne de commande"""
    cmd = command.split("|")[0].split(">")[0].split("<")[0].strip()

    while "=" in cmd.split()[0] if cmd.split() else False:
        parts = cmd.split(maxsplit=1)
        if len(parts) > 1:
            cmd = parts[1]
        else:
            break

    try:
        parts = shlex.split(cmd)
        if parts:
            return parts[0].split("/")[-1]
    except ValueError:
        parts = cmd.split()
        if parts:
            return parts[0].split("/")[-1]

    return ""


def validate_command(command: str) -> tuple[bool, str]:
    """Valider une commande - Mode autonome = blacklist"""
    if not command or not command.strip():
        return False, "Commande vide"

    command = command.strip()
    parts = command.split()
    if not parts:
        return False, "Commande vide"

    # Extraire commande de base
    base_cmd = parts[0].split("/")[-1]
    if base_cmd == "sudo" and len(parts) > 1:
        base_cmd = parts[1].split("/")[-1]

    # Vérifier blacklist
    if base_cmd in FORBIDDEN_COMMANDS:
        logger.warning(f"🚫 Commande interdite: {base_cmd}")
        return False, f"Commande '{base_cmd}' interdite"

    # Vérifier patterns dangereux
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            logger.warning(f"🚫 Pattern dangereux: {command[:50]}")
            return False, "Pattern dangereux détecté"

    # Mode autonome - tout le reste est OK
    logger.info(f"✅ Commande autorisée: {command[:60]}")
    return True, "OK"


def get_security_config() -> dict:
    """Config de sécurité"""
    return {
        "autonomous_mode": AUTONOMOUS_MODE,
        "forbidden_commands": list(FORBIDDEN_COMMANDS),
    }


# Compatibilité avec ancien code
def is_command_allowed(command: str) -> bool:
    allowed, _ = validate_command(command)
    return allowed


# ===== AUDIT LOGGING =====


class AuditLog:
    """Journalisation des actions pour audit de sécurité"""

    def __init__(self, log_file: str = "/data/audit.log"):
        self.log_file = log_file
        self.audit_logger = logging.getLogger("audit")

        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            handler = logging.FileHandler(log_file)
            handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
            self.audit_logger.addHandler(handler)
            self.audit_logger.setLevel(logging.INFO)
        except Exception as e:
            logger.warning(f"Could not setup audit log file: {e}")

    def log_command(
        self, command: str, user: str = "anonymous", allowed: bool = True, reason: str = ""
    ):
        """Log une tentative d'exécution de commande"""
        status = "ALLOWED" if allowed else "BLOCKED"
        self.audit_logger.info(f"COMMAND|{status}|user={user}|cmd={command[:200]}|reason={reason}")

    def log_file_access(
        self,
        path: str,
        action: str,
        user: str = "anonymous",
        allowed: bool = True,
        reason: str = "",
    ):
        """Log une tentative d'accès fichier"""
        status = "ALLOWED" if allowed else "BLOCKED"
        self.audit_logger.info(
            f"FILE|{status}|user={user}|action={action}|path={path}|reason={reason}"
        )

    def log_auth(self, user: str, success: bool, ip: str = ""):
        """Log une tentative d'authentification"""
        status = "SUCCESS" if success else "FAILED"
        self.audit_logger.info(f"AUTH|{status}|user={user}|ip={ip}")

    def log_security_event(self, event_type: str, details: str, severity: str = "WARNING"):
        """Log un événement de sécurité"""
        self.audit_logger.log(
            getattr(logging, severity.upper(), logging.WARNING),
            f"SECURITY|{event_type}|{details}",
        )


# Instance globale d'audit
audit_log = AuditLog()
