"""
Module de sécurité pour AI Orchestrator v5.0 - Mode Autonome
Blacklist au lieu de whitelist pour autonomie maximale
"""

import re
import os
import logging
from typing import Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# MODE AUTONOME - Tout est permis sauf la blacklist
AUTONOMOUS_MODE = True

# Commandes INTERDITES (blacklist)
FORBIDDEN_COMMANDS = {
    "mkfs", "fdisk", "parted", "dd",
    "insmod", "rmmod", "modprobe",
}

# Patterns dangereux
FORBIDDEN_PATTERNS = [
    r"rm\s+-rf\s+/\s*$",
    r"rm\s+-rf\s+/\*",
    r">\s*/dev/sd[a-z]",
    r":(){ :|:& };:",
]

# Chemins interdits en écriture
FORBIDDEN_WRITE_PATHS = ["/boot", "/usr/bin", "/usr/sbin", "/bin", "/sbin", "/lib"]


def validate_command(command: str) -> Tuple[bool, str]:
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
