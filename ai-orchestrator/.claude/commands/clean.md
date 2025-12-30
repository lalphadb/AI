# Nettoyage du code

Effectue un nettoyage complet:

1. **Format avec black**:
```bash
python3 -m black --line-length 100 backend/
```

2. **Trie les imports avec isort**:
```bash
python3 -m isort backend/
```

3. **Trouve les imports inutilisés**:
```bash
flake8 --select=F401 backend/
```

4. **Trouve les variables inutilisées**:
```bash
flake8 --select=F841 backend/
```

5. **Supprime les fichiers .pyc et __pycache__**:
```bash
find backend/ -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find backend/ -name "*.pyc" -delete 2>/dev/null
```

Pour chaque import/variable inutilisé trouvé, supprime-le du fichier concerné.
