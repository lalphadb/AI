# AI Orchestrator v5.2 - Agent Autonome Intelligent

L'AI Orchestrator est un **agent autonome avancé** conçu pour gérer l'infrastructure de 4LB.ca. Il combine la puissance des LLMs (via Ollama) avec une exécution d'outils système sécurisée, une mémoire sémantique persistante (ChromaDB), et un système d'auto-guérison.

## Fonctionnalités Principales

- **Boucle ReAct** - Raisonnement "Think, Plan, Act" pour résoudre des tâches complexes
- **Mode Autonome** - L'agent décide et agit avec une approche blacklist (pas whitelist)
- **Mémoire Sémantique** - ChromaDB pour mémoriser projets, préférences et faits techniques
- **Auto-Apprentissage** - Extraction automatique d'informations des conversations
- **Self-Healing** - Surveillance et réparation automatique du système
- **Multi-Modèles** - Support de Qwen, DeepSeek, Llama Vision et modèles cloud
- **Interface Temps Réel** - Frontend WebSocket avec affichage de la "pensée" de l'IA

## Architecture

```
+------------------+     +------------------+     +------------------+
|    Frontend      |<--->|    Backend       |<--->|    Ollama LLM    |
|    (Nginx)       | WSS |    (FastAPI)     | HTTP|    (Qwen/DS)     |
+------------------+     +--------+---------+     +------------------+
                                  |
                    +-------------+-------------+
                    |             |             |
              +-----v----+  +-----v----+  +-----v----+
              | ChromaDB |  |  SQLite  |  |   Host   |
              | (Memory) |  |   (DB)   |  |   (SSH)  |
              +----------+  +----------+  +----------+
```

## Stack Technologique

| Composant | Technologie |
|-----------|-------------|
| Backend | Python 3.13, FastAPI, Uvicorn |
| Frontend | HTML5, TailwindCSS, Vanilla JS |
| LLM | Ollama (Qwen 2.5 Coder, DeepSeek, Llama Vision) |
| Mémoire | ChromaDB (recherche sémantique) |
| Base de données | SQLite (conversations, auth) |
| Authentification | JWT + API Keys |
| Sécurité | Rate Limiting, Blacklist, Audit Logging |
| Déploiement | Docker, Docker Compose, Traefik |

## Installation Rapide

### Prérequis

- Docker et Docker Compose
- Ollama avec les modèles (qwen2.5-coder:32b, llama3.2-vision:11b)
- Réseau Docker `unified-net`

### Déploiement

```bash
# Cloner le projet
git clone https://github.com/4lb/ai-orchestrator.git
cd ai-orchestrator

# Configurer l'environnement
cp backend/.env.example backend/.env
# Éditer .env avec vos secrets

# Démarrer
docker compose up -d

# Vérifier
curl http://localhost:8001/health
```

### Configuration Minimale (.env)

```bash
AI_JWT_SECRET_KEY=votre-cle-secrete-32-caracteres
AI_ADMIN_PASSWORD=mot-de-passe-fort
AI_AUTH_ENABLED=true
AI_RATE_LIMIT_ENABLED=true
```

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture détaillée, flux de données |
| [API.md](docs/API.md) | Référence complète de l'API REST/WebSocket |
| [TOOLS.md](docs/TOOLS.md) | Documentation de tous les outils disponibles |
| [SECURITY.md](docs/SECURITY.md) | Guide de sécurité et bonnes pratiques |
| [UPGRADE.md](docs/UPGRADE.md) | Guide de migration entre versions |

## Outils Disponibles (55+)

### Système
- `execute_command` - Exécuter une commande shell
- `system_info` - Informations système (CPU, RAM, GPU)
- `service_status` / `service_control` - Gestion services systemd
- `disk_usage` - Analyse espace disque
- `process_list` - Liste des processus
- `logs_view` - Lecture des logs journalctl

### Docker
- `docker_status` - Liste des conteneurs
- `docker_logs` - Logs d'un conteneur
- `docker_restart` - Redémarrage conteneur
- `docker_compose` - Commandes docker compose
- `docker_exec` - Exécution dans un conteneur
- `docker_stats` - Statistiques Docker

### Fichiers
- `read_file` / `write_file` - Lecture/écriture fichiers
- `list_directory` - Listing répertoire
- `search_files` - Recherche par pattern
- `file_info` - Informations fichier

### Git
- `git_status` / `git_diff` - Statut et différences
- `git_log` / `git_branch` - Historique et branches
- `git_pull` - Pull modifications

### Mémoire
- `memory_store` / `memory_recall` - Stockage/rappel sémantique
- `memory_list` / `memory_delete` - Gestion mémoire
- `memory_stats` - Statistiques mémoire

### Réseau
- `network_info` - Informations réseau
- `port_check` - Vérification ports
- `dns_lookup` - Résolution DNS

## API Principales

### Authentification

```bash
# Login
curl -X POST https://ai.4lb.ca/api/auth/login \
  -d "username=admin&password=votremotdepasse"

# Réponse
{"access_token": "eyJ...", "refresh_token": "xyz...", "expires_in": 3600}
```

### Chat

```bash
curl -X POST https://ai.4lb.ca/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Liste les containers Docker", "model": "auto"}'
```

### WebSocket

```javascript
const ws = new WebSocket('wss://ai.4lb.ca/ws/chat?token=TOKEN');
ws.send(JSON.stringify({message: "Status Docker", model: "auto"}));
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

## Sécurité

- **Mode Autonome** - Blacklist des commandes dangereuses (mkfs, dd, rm -rf /)
- **JWT** - Tokens signés avec expiration (1h access, 7j refresh)
- **Rate Limiting** - 60 req/min par défaut
- **Audit Log** - Toutes les actions tracées
- **CSP** - Content Security Policy strict sur le frontend

## Self-Healing

Le service de self-healing surveille automatiquement:
- Espace disque (alerte si > 90%)
- Accessibilité Docker
- Charge système (alerte si > 20.0)

En cas de problème, l'agent lance automatiquement une session de réparation.

## Changelog v5.2

### Nouveautés
- **55 outils** - Outils Ollama + outils méta pour auto-amélioration
- **RAG v2** - Embeddings mxbai-embed-large (1024 dim), 53 documents indexés
- **Chunking intelligent** - Découpage sémantique pour code, markdown, texte
- **File Indexer** - Indexation automatique de fichiers avec watcher
- **Retry 429** - Gestion automatique des erreurs rate-limit Ollama
- **Self-Healing optimisé** - Seuil de charge système ajusté
- **Engine robuste** - Extraction final_answer améliorée pour texte français

### v5.1 (précédent)
- Engine optimisé - Meilleure extraction des réponses finales
- Outils modulaires - Chargement dynamique avec rechargement à chaud
- Mode Autonome - Approche blacklist pour plus de flexibilité
- SSH transparent - Exécution de commandes sur l'hôte via SSH
- Self-Healing - Service de surveillance et réparation automatique
- Frontend v4.1 - Gestion améliorée des tokens et reconnexion

## Contribution

Les contributions sont bienvenues. Toute modification des outils système doit respecter le module `security.py`.

```bash
# Lancer les tests
cd backend
python -m pytest tests/

# Vérifier la syntaxe
python3 -m py_compile main.py engine.py
```

## Support

- Issues: [GitHub Issues](https://github.com/4lb/ai-orchestrator/issues)
- Sécurité: security@4lb.ca

---

**Version**: 5.2.0
**Auteur**: 4LB.ca
**Licence**: MIT
