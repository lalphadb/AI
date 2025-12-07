#!/usr/bin/env python3
# Test de connexion PostfixAdmin avec Python

import requests
from urllib.parse import urljoin

print("🤖 TEST AUTOMATIQUE DE CONNEXION POSTFIXADMIN")
print("=============================================\n")

# Configuration
base_url = "http://4lb.ca"
login_url = urljoin(base_url, "/mailadmin/login.php")

# Comptes à tester
accounts = [
    {"email": "admin@4lb.ca", "password": "admin"},
    {"email": "test@4lb.ca", "password": "test"},
    {"email": "admin@4lb.ca", "password": "password123"},
]

# Créer une session pour gérer les cookies
session = requests.Session()

print(f"📍 URL de test: {login_url}\n")

for account in accounts:
    print(f"\n🔐 Test avec: {account['email']} / {account['password']}")
    print("-" * 50)
    
    try:
        # D'abord, obtenir la page de login pour récupérer les cookies/tokens
        response = session.get(login_url)
        print(f"  GET /login.php: {response.status_code}")
        
        # Préparer les données du formulaire
        login_data = {
            "fUsername": account["email"],
            "fPassword": account["password"],
            "lang": "en",
            "submit": "Login"
        }
        
        # Essayer différentes variantes de noms de champs
        variants = [
            {"fUsername": account["email"], "fPassword": account["password"], "submit": "Login"},
            {"username": account["email"], "password": account["password"], "submit": "Login"},
            {"login": account["email"], "password": account["password"], "submit": "Login"},
        ]
        
        for data in variants:
            # Poster les données de connexion
            response = session.post(login_url, data=data, allow_redirects=True)
            
            print(f"  POST avec {list(data.keys())}: {response.status_code}")
            print(f"  URL finale: {response.url}")
            
            # Vérifier le contenu de la réponse
            content = response.text.lower()
            
            if "logout" in content or "domain list" in content or "main.php" in response.url:
                print("  🎉 CONNEXION RÉUSSIE !")
                print(f"  Cookies: {session.cookies.get_dict()}")
                
                # Sauvegarder la page de succès
                with open(f"/home/studiosdb/success_{account['email'].replace('@', '_')}.html", "w") as f:
                    f.write(response.text)
                print("  📄 Page sauvegardée")
                break
                
            elif "incorrect" in content or "invalid" in content or "failed" in content:
                print("  ❌ Identifiants incorrects")
                
                # Chercher le message d'erreur exact
                for line in response.text.split('\n'):
                    if 'incorrect' in line.lower() or 'error' in line.lower():
                        print(f"     Message: {line.strip()[:100]}")
                        break
            else:
                print("  ⚠️ Résultat incertain")
                
                # Sauvegarder pour analyse
                with open(f"/home/studiosdb/test_{account['email'].replace('@', '_')}.html", "w") as f:
                    f.write(response.text)
                    
    except Exception as e:
        print(f"  ❌ Erreur: {str(e)}")

print("\n" + "=" * 50)
print("🏁 TEST TERMINÉ")
