# Audit Report – AI Orchestrator (2025-12-25)

## Scope & Method
- Parcours complet du dépôt (`backend`, `frontend`, `docs`, scripts Docker/compose) pour identifier les risques de sécurité/fonctionnement.
- Lecture ciblée des modules sensibles (auth, sécurité, outils système/Docker, moteur ReAct, frontend WebSocket) et des tests.
- Tentative d’exécution de la suite de tests avec l’environnement fourni.
  - `backend/venv/bin/python -m pytest tests -q` → échec immédiat: `No module named pytest` (dépendances de test absentes dans le venv livré).

## Vue d’ensemble du dépôt
- `backend/`: FastAPI + moteur ReAct + outils d’exécution (sécurité, auth, rate limiting, mémoire) et scripts de sauvegarde.
- `frontend/`: single page app HTML/JS autonome (WebSocket, dashboard temps réel, uploads frontaux).
- `docs/` + fichiers Compose/Nginx décrivant le déploiement (backend + frontend uniquement, pas de service mémoire).

## Principales constatations
### Critique
1. **Refresh tokens mappés systématiquement sur l’admin** (`backend/main.py:627-663`)
   - `create_refresh_token` est appelé avec `user_id=1` quel que soit l’utilisateur connecté et l’endpoint `/api/auth/refresh` recharge systématiquement `get_user("admin")`. Toute API key/JWT rafraîchi donne donc des droits admin et un utilisateur non-admin ne peut jamais récupérer ses propres scopes.
   - Les paramètres `refresh_token` de `refresh`/`logout` sont attendus en query string alors que la documentation et les clients front envoient du JSON, ce qui les rend inutilisables.
   - **Impact**: escalade de privilèges triviale + impossibilité de maintenir une session propre par utilisateur.
   - **Action**: stocker `user_id` réel au login, accepter un corps JSON (`refresh_token: str = Body(...)`), recharger l’utilisateur correspondant et révoquer spécifiquement son token.

2. **Le “sandbox” de sécurité est contourné par la majorité des outils** (`backend/tools/__init__.py:33-85`, `backend/tools/system_tools.py:33-101`).
   - Seuls `execute_command`, `read_file`, `write_file` reçoivent les validateurs; les autres (Docker, services, Git, réseau…) exécutent les commandes brutes, parfois même via `sudo systemctl` (`backend/tools/system_tools.py:69-86`).
   - Un utilisateur authentifié peut donc forcer des `systemctl restart`, `docker exec`, `git pull`, etc. sans aucune vérification de whitelist ni audit, ce qui annule les garanties du module `security.py`.
   - **Action**: faire transiter `security_validator`/`audit_logger` dans TOUS les handlers sensibles, supprimer l’usage de `sudo`, valider explicitement services/containers autorisés et journaliser chaque action.

### Élevé
3. **La plupart des commandes d’outils ne fonctionnent pas (pipes/redirections incompatibles avec `run_command_async`)**
   - Le wrapper (`backend/utils/async_subprocess.py:33-84`) exécute les commandes via `execve` sans shell, mais l’implémentation des outils continue d’utiliser `|`, `&&`, `2>/dev/null`, etc. (ex: `system_info` ligne `lscpu | head -20`, `disk_usage` ligne 108, `docker_logs` ligne 64, `docker_compose` ligne 105, `list_directory` ligne 108, `search_files` ligne 135, `port_scan` ligne 104).
   - Résultat: ces commandes échouent silencieusement ou interprètent `2>&1`/`||` comme arguments, ce qui explique l’absence de métriques/logs fiables côté agent.
   - **Action**: soit ré-écrire chaque commande en listes d’arguments (exécuter `head` séparément, filtrer côté Python), soit créer un exécuteur sécurisé type `bash -lc` encapsulé par le validateur et limiter strictement les entrées.

4. **Flux WebSocket/Frontend cassé (conversations, Docker, fichiers)** (`frontend/index.html:269-357`, `backend/main.py:901-934`).
   - Le client ne traite pas les messages `conversation_created`/`model_selected`; `currentConversationId` reste `null` et chaque envoi crée une nouvelle conversation côté serveur.
   - `loadConversations()` suppose que `GET /api/conversations` retourne un tableau alors que l’API renvoie `{ "conversations": [...] }`, d’où une liste vide (ligne 353 vs `backend/main.py:993-998`).
   - Le panneau Docker appelle `/api/docker/status` (ligne 356) qui n’existe pas dans l’API; le bouton affiche donc systématiquement “Erreur chargement”.
   - Les pièces jointes sont envoyées inline (`files: attachedFiles` ligne 290) alors que le backend attend des `file_ids` issus de `/api/upload`; aucune requête d’upload n’est effectuée.
   - **Action**: 1) stocker `conversation_id` lors de l’évènement WebSocket, 2) adapter `loadConversations` pour lire `response.conversations`, 3) exposer un endpoint Docker ou retirer l’appel, 4) téléverser les fichiers via `/api/upload` puis passer `file_ids` à WS.

### Moyen
5. **L’outil `analyze_image` est inutilisable** (`backend/tools/ai_tools.py:23-54`).
   - Il attend `uploaded_files.items()` (dict id→métadonnées) alors que `execute_tool` transmet une `list` de lignes DB (`backend/main.py:901-915`). L’appel provoque `AttributeError` dès qu’un modèle vision est sollicité.
   - **Action**: convertir la liste en dict coté backend ou adapter l’outil à la structure existante.

6. **Mémoire/Auto-learn inopérants par défaut** (`docker-compose.yml:1-40`, `backend/auto_learn.py:53-63`, `backend/tools/memory_tools.py:27-52`).
   - Le docker-compose ne déploie que `backend` + `frontend` mais les modules mémoire se connectent à `chromadb:8000`. Sans conteneur externe, tout appel à `memory_*`/`auto_learn` échoue.
   - **Action**: ajouter un service ChromaDB partagé (volume de persistance, variables d’environnement cohérentes) ou rendre l’hôte configurable via `.env`.

7. **Fuite de secret JWT dans les logs** (`backend/auth.py:26-35`).
   - La clé secrète est affichée à chaque démarrage (“Loaded SECRET_KEY starting with …”). En production, les logs Traefik/systemd exposent donc un fragment du secret.
   - **Action**: supprimer ce `print`, consigner une empreinte neutre au besoin.

8. **Montage de `/home/lalpha` en lecture/écriture dans le conteneur backend** (`docker-compose.yml:14-24`).
   - Le conteneur a accès complet à tout le home (clé SSH, repos privés, secrets) alors que l’objectif est justement d’isoler les actions orchestrées. Un compromis du backend compromet tout l’hôte.
   - **Action**: limiter les montages aux répertoires nécessaires (`/home/lalpha/projets` en ro, dossiers spécifiques en rw) et utiliser des comptes techniques dédiés.

## Situation des tests
- **Échec**: `backend/venv/bin/python -m pytest tests -q`
  - Raison: le venv commité n’embarque pas `pytest`. Il est donc impossible de valider automatiquement les modules (sécurité, auth, rate limiter) sans recréer un environnement propre ou installer les dépendances manquantes.
  - **Action rapide**: documenter l’installation (`pip install -r requirements.txt && pip install -r requirements-dev.txt`) et ajouter un workflow de test.

## Plan de correction recommandé (par étapes)
1. **Assainir l’authentification**
   - Corriger la gestion des refresh tokens (stockage `user_id`, payload, endpoints Body) et supprimer l’affichage du secret.
   - Ajouter des tests de régression pour login/refresh/logout.
2. **Réactiver réellement la couche de sécurité**
   - Propager `security_validator` et `audit_logger` à tous les handlers d’outils, retirer `sudo`, restreindre services/containers autorisés et auditer chaque action.
3. **Fiabiliser l’exécution des commandes**
   - Réécrire les outils utilisant pipes/redirections pour qu’ils fonctionnent avec `run_command_async` (ou définir un exécuteur “sécurisé” unique) et couvrir ces cas par tests (ex: `disk_usage`, `docker_logs`).
4. **Réparer le frontend temps réel**
   - Gérer les évènements WebSocket supplémentaires, corriger `loadConversations`, implémenter l’upload des fichiers et, soit exposer `/api/docker/status`, soit supprimer l’UI correspondante.
5. **Rendre la mémoire fonctionnelle**
   - Ajouter un service ChromaDB (ou configuration fallback), vérifier la connexion via health check et traiter l’absence de service côté UI.
6. **Renforcer le déploiement**
   - Réduire les montages sensibles, documenter les variables `.env`, ajouter un script de smoke-test (health, auth, outils critiques) exécuté en CI/CD avant mise en prod.
7. **Outillage/tests**
   - Ajouter les dépendances de test, exécuter `pytest backend/tests` en CI et couvrir au moins les flux corrigés (auth refresh, outils essentiels, WebSocket handler via tests unitaires/mocks).

Ce rapport reste disponible dans `AUDIT_REPORT.md` pour consultation et suivi.
