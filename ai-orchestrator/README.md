# AI Orchestrator v5.1 - Agent Autonome Intelligent

L'AI Orchestrator est un **agent autonome avance** concu pour gerer l'infrastructure de 4LB.ca. Il combine la puissance des LLMs (via Ollama) avec une execution d'outils systeme securisee, une memoire semantique persistante (ChromaDB), et un systeme d'auto-guerison.

## Fonctionnalites Principales

- **Boucle ReAct** - Raisonnement "Think, Plan, Act" pour resoudre des taches complexes
- **Mode Autonome** - L'agent decide et agit avec une approche blacklist (pas whitelist)
- **Memoire Semantique** - ChromaDB pour memoriser projets, preferences et faits techniques
- **Auto-Apprentissage** - Extraction automatique d'informations des conversations
- **Self-Healing** - Surveillance et reparation automatique du systeme
- **Multi-Modeles** - Support de Qwen, DeepSeek, Llama Vision et modeles cloud
- **Interface Temps Reel** - Frontend WebSocket avec affichage de la "pensee" de l'IA

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
| Memoire | ChromaDB (recherche semantique) |
| Base de donnees | SQLite (conversations, auth) |
| Authentification | JWT + API Keys |
| Securite | Rate Limiting, Blacklist, Audit Logging |
| Deploiement | Docker, Docker Compose, Traefik |

## Installation Rapide

### Prerequis

- Docker et Docker Compose
- Ollama avec les modeles (qwen2.5-coder:32b, llama3.2-vision:11b)
- Reseau Docker `unified-net`

### Deploiement

```bash
# Cloner le projet
git clone https://github.com/4lb/ai-orchestrator.git
cd ai-orchestrator

# Configurer l'environnement
cp backend/.env.example backend/.env
# Editer .env avec vos secrets

# Demarrer
docker compose up -d

# Verifier
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
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture detaillee, flux de donnees |
| [API.md](docs/API.md) | Reference complete de l'API REST/WebSocket |
| [TOOLS.md](docs/TOOLS.md) | Documentation de tous les outils disponibles |
| [SECURITY.md](docs/SECURITY.md) | Guide de securite et bonnes pratiques |
| [UPGRADE.md](docs/UPGRADE.md) | Guide de migration entre versions |

## Outils Disponibles

### Systeme
- `execute_command` - Executer une commande shell
- `system_info` - Informations systeme (CPU, RAM, GPU)
- `service_status` / `service_control` - Gestion services systemd
- `disk_usage` - Analyse espace disque
- `process_list` - Liste des processus
- `logs_view` - Lecture des logs journalctl

### Docker
- `docker_status` - Liste des conteneurs
- `docker_logs` - Logs d'un conteneur
- `docker_restart` - Redemarrage conteneur
- `docker_compose` - Commandes docker compose
- `docker_exec` - Execution dans un conteneur
- `docker_stats` - Statistiques Docker

### Fichiers
- `read_file` / `write_file` - Lecture/ecriture fichiers
- `list_directory` - Listing repertoire
- `search_files` - Recherche par pattern
- `file_info` - Informations fichier

### Git
- `git_status` / `git_diff` - Statut et differences
- `git_log` / `git_branch` - Historique et branches
- `git_pull` - Pull modifications

### Memoire
- `memory_store` / `memory_recall` - Stockage/rappel semantique
- `memory_list` / `memory_delete` - Gestion memoire

## API Principales

### Authentification

```bash
# Login
curl -X POST https://ai.4lb.ca/api/auth/login \
  -d "username=admin&password=votremotdepasse"

# Reponse
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

## Securite

- **Mode Autonome** - Blacklist des commandes dangereuses (mkfs, dd, rm -rf /)
- **JWT** - Tokens signes avec expiration (1h access, 7j refresh)
- **Rate Limiting** - 60 req/min par defaut
- **Audit Log** - Toutes les actions tracees
- **CSP** - Content Security Policy strict sur le frontend

## Self-Healing

Le service de self-healing surveille automatiquement:
- Espace disque (alerte si > 90%)
- Accessibilite Docker
- Charge systeme (alerte si > 4.0)

En cas de probleme, l'agent lance automatiquement une session de reparation.

## Changelog v5.1

- **Engine optimise** - Meilleure extraction des reponses finales
- **Outils modulaires** - Chargement dynamique avec rechargement a chaud
- **Mode Autonome** - Approche blacklist pour plus de flexibilite
- **SSH transparent** - Execution de commandes sur l'hote via SSH
- **Self-Healing** - Service de surveillance et reparation automatique
- **Frontend v4.1** - Gestion amelioree des tokens et reconnexion

## Contribution

Les contributions sont bienvenues. Toute modification des outils systeme doit respecter le module `security.py`.

```bash
# Lancer les tests
cd backend
python -m pytest tests/

# Verifier la syntaxe
python3 -m py_compile main.py engine.py
```

## Support

- Issues: [GitHub Issues](https://github.com/4lb/ai-orchestrator/issues)
- Securite: security@4lb.ca

---

**Version**: 5.1.0
**Auteur**: 4LB.ca
**Licence**: MIT
