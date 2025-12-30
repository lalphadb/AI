# Test du projet

Lance les vérifications complètes:

1. **Syntaxe Python**: Vérifie tous les fichiers .py
```bash
python3 -m py_compile backend/main.py backend/engine.py backend/prompts.py backend/config.py backend/security.py
python3 -m py_compile backend/tools/*.py
```

2. **Lint**: Vérifie les erreurs importantes
```bash
flake8 --select=E999,F821,F811 backend/ --max-line-length=120
```

3. **API Health**: Vérifie que l'API répond
```bash
curl -s http://localhost:8001/health | jq
```

4. **Container status**: Vérifie Docker
```bash
docker ps --filter "name=ai-orchestrator" --format "table {{.Names}}\t{{.Status}}"
```

Corrige automatiquement les erreurs trouvées.
