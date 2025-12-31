#!/usr/bin/env python3
"""
Test de Preuve de Sécurité (Security Proof of Concept)
Valide que la faille d'injection de commande (RCE) est bien corrigée.
"""

import asyncio
import os
import sys
import pytest

# Ajouter le dossier parent au path pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.mark.asyncio
async def test_rce_protection():
    """Valide que l'injection de commande est bloquée"""
    from utils.async_subprocess import run_command_async
    
    print("🛡️  TEST DE SÉCURITÉ : Tentative d'injection de commande...")

    # Payload: Une commande inoffensive suivie d'une "injection"
    payload = "echo 'SAFE' ; whoami"

    output, code = await run_command_async(payload)

    # Analyse
    # Si le système est sûr, 'whoami' n'est pas exécuté par le shell
    # mais passé comme argument à echo (ou échoue car echo n'accepte pas ; comme séparateur sans shell).
    
    current_user = os.getlogin()
    
    # Avec le fix, le ';' n'est plus interprété comme un séparateur de commande par le shell
    # car on utilise create_subprocess_exec (via shlex.split).
    # 'echo' recevra les arguments ["'SAFE'", ";", "whoami"]
    
    is_vulnerable = current_user in output and "SAFE" in output and ";" not in output
    
    assert not is_vulnerable, "🚨 INJECTION RÉUSSIE ! Le système est VULNÉRABLE."
    
    # On s'attend à ce que 'whoami' soit présent dans l'output de echo (comme texte)
    # OU que la commande échoue si echo ne supporte pas ces arguments (selon l'OS).
    if "whoami" in output:
        print("\n✅ SUCCÈS : L'injection a échoué (interprété comme simple texte par echo).")
    else:
        print("\n✅ SUCCÈS : L'injection a échoué (la commande n'a pas été exécutée par le shell).")