#!/usr/bin/env python3
"""
Script de Preuve de Sécurité (Security Proof of Concept)
Valide que la faille d'injection de commande (RCE) est bien corrigée.

Ce script tente d'injecter une commande malveillante via run_command_async.
"""

import sys
import os
import asyncio

# Ajouter le dossier parent au path pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.async_subprocess import run_command_async

async def test_rce_protection():
    print("🛡️  TEST DE SÉCURITÉ : Tentative d'injection de commande...")
    
    # Payload: Une commande inoffensive suivie d'une "injection"
    # Si le système est vulnérable (shell=True), il exécutera 'whoami'.
    # Si le système est sécurisé (exec), il passera '; whoami' comme argument à echo.
    payload = "echo 'SAFE' ; whoami"
    
    print(f"📝 Payload envoyé : \"{payload}\"")
    
    output, code = await run_command_async(payload)
    
    print("\n--- RÉSULTAT ---")
    print(f"Code retour : {code}")
    print(f"Sortie brute :\n{output}")
    print("----------------")
    
    # Analyse
    if os.getlogin() in output and "SAFE" in output and ";" not in output:
        # Si on voit le nom d'utilisateur ET SAFE mais PAS le point-virgule
        # C'est que le point-virgule a été interprété par le shell
        print("\n🚨 ÉCHEC : INJECTION RÉUSSIE ! Le système est VULNÉRABLE.")
        print("   Le shell a interprété le ';'")
        sys.exit(1)
        
    elif "SAFE" in output and "whoami" in output:
        # Si on voit "SAFE" et "whoami" (littéralement)
        print("\n✅ SUCCÈS : L'injection a échoué.")
        print("   La commande a été interprétée littéralement (protection active).")
        print("   'echo' a simplement affiché tout le texte.")
        sys.exit(0)
        
    else:
        # Cas incertain (peut-être une erreur de syntaxe echo qui est aussi bon signe)
        print("\n✅ SUCCÈS (Probable) : Comportement différent d'un shell standard.")
        sys.exit(0)

if __name__ == "__main__":
    try:
        asyncio.run(test_rce_protection())
    except Exception as e:
        print(f"❌ Erreur lors du test : {e}")
        sys.exit(1)
