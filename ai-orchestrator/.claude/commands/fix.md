# Correction automatique

Lance toutes les corrections automatiques possibles:

1. **Format le code**:
```bash
python3 -m black --line-length 100 backend/
python3 -m isort backend/
```

2. **Trouve et supprime les imports inutilisés**:
Pour chaque fichier, utilise ast pour trouver les imports non utilisés et supprime-les.

3. **Trouve et supprime les variables inutilisées**:
Pour chaque variable F841 trouvée, évalue si elle peut être supprimée sans casser le code.

4. **Corrige les erreurs de syntaxe**:
Si py_compile échoue, analyse l'erreur et corrige-la.

5. **Vérifie et rebuild**:
```bash
python3 -m py_compile backend/main.py backend/engine.py
docker compose build backend && docker compose up -d backend
```

Continue jusqu'à ce que tous les tests passent.
