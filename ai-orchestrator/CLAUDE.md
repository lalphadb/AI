# AI Orchestrator - Instructions Claude Code

## 🎯 MISSION
Tu es l'assistant de développement pour AI Orchestrator, un agent ReAct autonome.
Tu dois coder de manière **AUTONOME**, **TESTER**, **CORRIGER** et **NETTOYER** le code.

## 🚀 MODE AUTONOME - RÈGLES

### 1. NE PAS DEMANDER PERMISSION POUR:
- Lire/écrire des fichiers dans ce projet
- Exécuter des commandes git, docker, python
- Créer des fichiers de test
- Corriger des erreurs de syntaxe
- Formater le code
- Supprimer du code mort

### 2. TOUJOURS FAIRE AUTOMATIQUEMENT:
- Tester le code après modification (`python3 -m py_compile`)
- Vérifier les imports inutilisés
- Lancer les tests existants si présents
- Rebuild Docker si modification backend
- Vérifier les logs après restart

### 3. WORKFLOW DE DÉVELOPPEMENT:
```
1. ANALYSER → Comprendre la demande et le contexte
2. PLANIFIER → Lister les fichiers à modifier
3. CODER → Implémenter les changements
4. TESTER → Vérifier syntaxe + tests unitaires
5. CORRIGER → Fixer les erreurs automatiquement
6. NETTOYER → Supprimer code mort, imports inutiles
7. DÉPLOYER → Rebuild Docker si nécessaire
8. VÉRIFIER → Checker les logs et le health
```

## 📁 STRUCTURE DU PROJET
```
ai-orchestrator/
├── backend/
│   ├── main.py          # FastAPI + WebSocket + Auth
│   ├── engine.py        # Boucle ReAct (THINK→PLAN→ACTION→OBSERVE)
│   ├── prompts.py       # System prompts + router factuel/opérationnel
│   ├── config.py        # Config modèles LLM (9 modèles)
│   ├── security.py      # Validation commandes (blacklist)
│   ├── tools/           # 54+ outils disponibles
│   │   ├── __init__.py      # Registry des outils
│   │   ├── system_tools.py  # execute_command, system_info
│   │   ├── docker_tools.py  # Docker management
│   │   ├── file_tools.py    # Lecture/écriture fichiers
│   │   └── memory_tools.py  # ChromaDB mémoire sémantique
│   └── data/            # SQLite + données persistantes
├── frontend/
│   └── index.html       # Interface web (servi par nginx)
├── docker-compose.yml   # Services: backend + frontend
├── .env                 # Variables d'environnement
└── CLAUDE.md            # Ce fichier
```

## 🔧 COMMANDES UTILES

### Développement
```bash
# Test syntaxe Python
python3 -m py_compile backend/main.py backend/engine.py backend/prompts.py

# Lint (erreurs importantes)
flake8 --select=E,F backend/ --max-line-length=120

# Format
black --line-length 100 backend/
isort backend/

# Trouver imports inutilisés
flake8 --select=F401 backend/

# Trouver variables inutilisées
flake8 --select=F841 backend/
```

### Docker
```bash
# Rebuild + restart backend
docker compose build backend && docker compose up -d backend

# Voir les logs (suivre)
docker logs -f ai-orchestrator-backend

# Vérifier santé
docker ps --filter "name=ai-orchestrator" --format "{{.Names}}: {{.Status}}"

# Restart complet
docker compose down && docker compose up -d
```

### Debug
```bash
# Test API health
curl -s http://localhost:8001/health | jq

# Test API stats
curl -s http://localhost:8001/api/stats | jq

# Voir la DB
sqlite3 backend/data/orchestrator.db ".tables"
sqlite3 backend/data/orchestrator.db "SELECT COUNT(*) FROM messages"

# Logs récents
docker logs ai-orchestrator-backend 2>&1 | tail -50
```

## 🔴 POINTS CRITIQUES

### Corrections P0 (NE PAS CASSER)
1. **P0-1**: Validation anti-réponse vide dans `main.py:443-461`
2. **P0-2**: Collecte résultats + fallback dans `engine.py:148-320`
3. **P0-3**: Logs THINK/ACTION/OBSERVE dans `engine.py:246-290`

### Fichiers Sensibles
- `.env` → Ne JAMAIS commiter les secrets
- `docker-compose.yml` → Attention aux ports/volumes
- `security.py` → Blacklist des commandes dangereuses

## 🧹 NETTOYAGE DU CODE

### Checklist avant commit:
- [ ] Aucune erreur de syntaxe
- [ ] Aucun import inutilisé (F401)
- [ ] Aucune variable inutilisée (F841)
- [ ] Code formaté avec black
- [ ] Tests passent
- [ ] Docker rebuild OK
- [ ] Logs propres

### Commande nettoyage complet:
```bash
cd /home/lalpha/projets/ai-tools/ai-orchestrator
black --line-length 100 backend/
isort backend/
flake8 --select=F401,F841 backend/ | head -20
python3 -m py_compile backend/*.py backend/tools/*.py
```

## 🧪 TESTS

### Test manuel rapide:
```python
# Dans un fichier test_quick.py
import sys
sys.path.insert(0, 'backend')
from engine import react_loop
from prompts import classify_query

# Test router
assert classify_query("uptime serveur") == "operational"
assert classify_query("c'est quoi Docker") == "factual"
print("✅ Tests OK")
```

### Vérifier le système en production:
```bash
# 1. API répond
curl -s http://localhost:8001/health

# 2. WebSocket fonctionne (check logs)
docker logs ai-orchestrator-backend 2>&1 | grep -i "websocket"

# 3. Outils chargés
curl -s http://localhost:8001/api/stats | jq '.tools_count // "N/A"'
```

## 📊 MODÈLES LLM DISPONIBLES
| Clé | Modèle | Usage |
|-----|--------|-------|
| `auto` | Sélection auto | Défaut recommandé |
| `qwen-coder` | qwen2.5-coder:32b | Code, scripts |
| `deepseek-coder` | deepseek-coder:33b | Algorithmes |
| `llama-vision` | llama3.2-vision:11b | Images, OCR |
| `qwen-vision` | qwen3-vl:32b | Multimodal |
| `kimi-k2` | Cloud | Modèle Moonshot |
| `gemini-pro` | Cloud | Google Gemini |
| `gpt-safeguard` | Local 13B | Sécurité |

## ⚡ RACCOURCIS

Pour être plus rapide, utilise ces patterns:

```bash
# Alias rebuild
alias reb="docker compose build backend && docker compose up -d backend && sleep 3 && docker logs ai-orchestrator-backend 2>&1 | tail -20"

# Alias test
alias pytest="python3 -m py_compile backend/main.py backend/engine.py && echo '✅ OK'"

# Alias clean
alias pyclean="black --line-length 100 backend/ && isort backend/"
```

---
**RAPPEL**: Tu as le mode AUTONOME activé. Code, teste, corrige et nettoie sans demander!
