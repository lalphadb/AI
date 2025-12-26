# AI Orchestrator – Audit Technique (v2)
_Date: 2025‑12‑25_

## 1. Méthodologie
- Inspection manuelle du dépôt (`backend`, `frontend`, `docs`, Dockerfiles, scripts) avec focus sécurité/comportement.
- Lecture ciblée des modules critiques: authentification, sécurité, outils système/Docker, boucle ReAct, frontend WS.
- Vérification des artefacts de déploiement (`docker-compose*`, `start.sh`, `nginx.conf`).
- Tentative d’exécution de la suite de tests (`backend/venv/bin/python -m pytest tests -q`).

## 2. Constatations principales
| # | Gravité | Chemin (réf) | Description |
|---|---------|--------------|-------------|
|1|Critique|`backend/main.py:600-666`|`create_refresh_token` est invoqué avec `user_id=1` pour tout le monde et `/api/auth/refresh` recharge toujours `get_user("admin")`. Toute session rafraîchie récupère les privilèges admin, et l’API attend le token en paramètre simple alors que la doc/le frontend envoient du JSON.|
|2|Critique|`backend/tools/__init__.py:33-89`, `backend/tools/system_tools.py:14-101`, `backend/tools/docker_tools.py:33-153`|Seuls trois outils bénéficient du validateur/audit. Tous les autres (Docker, services, Git, réseau…) exécutent directement `systemctl`, `docker`, `git`, parfois avec `sudo`, sans aucune vérification de whitelist ni journalisation. Un utilisateur authentifié peut donc lancer des commandes sensibles non prévues.|
|3|Élevée|`backend/utils/async_subprocess.py:33-84` + multiples outils|`run_command_async` exécute les commandes via `execve` sans shell; pourtant les outils utilisent encore `|`, `&&`, redirections et `cd … && …`. Résultat: erreurs silencieuses (pas de métriques, statut Docker vide). Exemples: `system_info` (`head`, pipes), `disk_usage` (`du ... | sort`), `list_directory` (`tree ... || find`), `docker_logs` (`2>&1`), `docker_compose` (`cd ... &&`).|
|4|Élevée|`frontend/index.html:269-357` vs `backend/main.py:901-1015`|Le frontend WS ne traite pas les messages `conversation_created`/`model_selected`, `loadConversations` suppose un tableau au lieu de `{"conversations": [...]}`, l’UI Docker appelle `/api/docker/status` inexistant, les fichiers sont envoyés inline (`files: attachedFiles`) alors que l’API attend des `file_ids` uploadés. L’expérience temps réel est donc cassée (nouvelle conversation à chaque envoi, pas d’uploads).|
|5|Élevée|`docker-compose.yml:1-40`, `docker-compose.simple.yml:1-28`|Le service backend monte `/home/lalpha` en lecture/écriture dans le conteneur et dépend d’un Ollama externe. Le service mémoire (`chromadb`) n’est pas déployé alors que `auto_learn`/`memory_*` s’y connectent par défaut; toutes les fonctions mémoire échouent.
|6|Moyenne|`backend/tools/ai_tools.py:23-73`|`analyze_image` attend `uploaded_files` sous forme de dict (`uploaded_files.items()`), mais `main.py` transmet une `list` (`uploaded_files.append(info)`). Le moindre appel vision provoque une exception.|
|7|Moyenne|`backend/main.py:470-481`|`delete_conversation` supprime les entrées DB/Uploads mais ne nettoie pas les fichiers sur disque (`data/uploads`). Les pièces jointes restent présentes indéfiniment, problème de conformité (droit à l’oubli).|
|8|Moyenne|`backend/auth.py:26-35`|La clé JWT est affichée au démarrage (“Loaded SECRET_KEY starting with …”). En production, les journaux exposent donc un fragment du secret.|
|9|Moyenne|`backend/auto_learn.py:53-63`, `backend/tools/memory_tools.py:27-52`|Le host Chroma est câblé sur `chromadb:8000` et ignore les variables définies dans `.env`. Impossible d’exécuter l’auto-apprentissage en local sans modifier le code.|
|10|Moyenne|`backend/.env`, `backend/venv/`|Le dépôt contient un `.env` et un environnement virtuel complet (packages binaires). Risque de fuite de secrets et de dépendances obsolètes; rend la reproductibilité/tests difficiles.|

### Autres points notables
- `backend/start.sh` lance directement `uvicorn` avec `OLLAMA_URL` local mais n’initialise ni Chroma ni variables d’auth (risque de démarrage en mode “anonymous”).
- De nombreux backups (`backend/_backups`, `frontend/*.backup`) sont versionnés; ils étendent inutilement la surface d’attaque et compliquent la maintenance.

## 3. Tests & validation
- Commande exécutée: `backend/venv/bin/python -m pytest tests -q` → **échec immédiat** (`No module named pytest`).
- Le venv commité n’embarque pas les dépendances de test; aucune validation automatique n’est possible tant que l’environnement n’est pas recréé (`pip install -r requirements.txt && pip install pytest pytest-asyncio ...`).

## 4. Plan de remédiation recommandé
1. **Revoir l’authentification**
   - Stocker le `user_id` réel dans `create_refresh_token`, accepter un body JSON pour `/api/auth/refresh` & `/api/auth/logout`, recharger l’utilisateur correspondant et respecter ses scopes.
   - Supprimer l’impression du secret JWT et ajouter des tests automatisés couvrant login/refresh/logout.
2. **Réactiver réellement la couche sécurité**
   - Propager `security_validator`/`audit_logger` vers tous les handlers (`tools/`), retirer l’usage de `sudo`, valider les services/containers autorisés et consigner chaque action.
3. **Rendre les outils compatibles avec `run_command_async`**
   - Réécrire les commandes multi-parties en appels séquentiels Python ou introduire un exécuteur sécurisé centralisé; vérifier chaque outil (Docker, fichiers, réseau) via tests.
4. **Corriger le frontend WebSocket**
   - Traiter les événements `conversation_created`, stocker `conversation_id`, adapter `loadConversations` au format `{"conversations": ...}`, téléverser les fichiers via `/api/upload` puis envoyer `file_ids`, créer un endpoint `/api/docker/status` ou supprimer l’onglet.
5. **Sécuriser le déploiement**
   - Limiter les montages Docker aux répertoires nécessaires (pas de `/home/lalpha` complet), ajouter un service ChromaDB (ou rendre l’hôte configurable via `.env`) et documenter clairement les variables sensibles.
6. **Hygiène du repo**
   - Retirer `backend/venv` et `.env` du contrôle de sources (utiliser `.env.example`), nettoyer les backups historiques, ajouter un workflow CI qui reconstruit l’environnement et exécute la suite pytest.
7. **Nettoyage des uploads**
   - Lors d’une suppression de conversation, supprimer physiquement les fichiers (`os.remove(info['filepath'])`) et consigner l’opération dans l’audit log.

## 5. Prochaines étapes suggérées
- Prioriser les correctifs critiques (auth/permissions) avant tout déploiement.
- Définir des tests de non-régression ciblant les outils sensibles et les flux WebSocket.
- Mettre en place une CI/CD qui (1) reconstruit l’image backend, (2) déploie un Chroma de test, (3) exécute les tests automatisés.
