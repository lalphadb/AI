# Déploiement

Effectue un déploiement complet:

1. **Test syntaxe** (obligatoire avant deploy):
```bash
python3 -m py_compile backend/main.py backend/engine.py backend/prompts.py
```

2. **Build Docker**:
```bash
docker compose build backend
```

3. **Restart containers**:
```bash
docker compose up -d backend
```

4. **Attendre que le container soit healthy**:
```bash
sleep 10
docker ps --filter "name=ai-orchestrator-backend" --format "{{.Names}}: {{.Status}}"
```

5. **Vérifier les logs**:
```bash
docker logs ai-orchestrator-backend 2>&1 | tail -30
```

6. **Test API**:
```bash
curl -s http://localhost:8001/health
```

Ne continue que si chaque étape réussit. En cas d'erreur, affiche les logs et corrige.
