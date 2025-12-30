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
    # mais passé comme argument à echo (ou échoue).
    # Donc on NE DOIT PAS voir le user courant si 'SAFE' est là et qu'on a tenté d'injecter.
    
    current_user = os.getlogin()
    
    # Échec si l'utilisateur est révélé ET que c'était une injection shell réussie
    is_vulnerable = current_user in output and "SAFE" in output and ";" not in output
    
    assert not is_vulnerable, "🚨 INJECTION RÉUSSIE ! Le système est VULNÉRABLE."
    
    # Succès si SAFE est affiché (commande echo a marché) et whoami est affiché littéralement
    # OU si le comportement montre que le shell n'a pas interprété le ;
    if "SAFE" in output and "whoami" in output:
        print("\n✅ SUCCÈS : L'injection a échoué (interprété littéralement).")
    else:
        print("\n✅ SUCCÈS (Probable) : Comportement différent d'un shell standard.")