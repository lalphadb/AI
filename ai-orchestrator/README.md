# AI Orchestrator v3.0

Agent IA autonome pour la gestion du serveur 4LB.ca avec boucle ReAct, mémoire sémantique et sécurité renforcée.

## Fonctionnalités

- **34 outils** - Système, Docker, Git, fichiers, réseau, mémoire
- **Boucle ReAct** - Raisonnement et action autonomes
- **Mémoire sémantique** - ChromaDB pour le contexte persistant
- **Auto-apprentissage** - Extraction automatique des faits
- **Multi-modèles** - 9 modèles LLM (locaux + cloud)
- **Vision** - Analyse d'images avec Llama Vision
- **Authentification JWT** - Tokens et API keys
- **Rate limiting** - Protection contre les abus
- **Validation de sécurité** - Commandes et chemins

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                     Traefik                         │
│                  (HTTPS/TLS)                        │
└─────────────────┬───────────────────────────────────┘
                  │
    ┌─────────────┴─────────────┐
    │                           │
┌───▼───────────┐   ┌───────────▼───────┐
│   Frontend    │   │     Backend       │
│   (nginx)     │   │   (FastAPI)       │
│   Port 80     │   │   Port 8001       │
└───────────────┘   └───────┬───────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
│   ChromaDB    │   │    Ollama     │   │    SQLite     │
│   Port 8000   │   │  Port 11434   │   │   /data/      │
└───────────────┘   └───────────────┘   └───────────────┘
```

## Installation

### Prérequis

- Docker & Docker Compose
- Ollama avec modèles installés
- ChromaDB
- Traefik (optionnel, pour HTTPS)

### Déploiement

```bash
# Cloner et configurer
cd /home/lalpha/projets/ai-tools/ai-orchestrator

# Configurer les variables d'environnement
cat > backend/.env << EOF
AI_JWT_SECRET_KEY=$(openssl rand -base64 32)
AI_ADMIN_PASSWORD=votre-mot-de-passe-fort
AI_AUTH_ENABLED=true
AI_RATE_LIMIT_ENABLED=true
AI_CORS_ORIGINS=["https://ai.4lb.ca"]
EOF

# Démarrer
docker compose up -d

# Vérifier
curl https://ai.4lb.ca/health
```

## Utilisation

### Interface Web

Accédez à https://ai.4lb.ca

### API

```bash
# Authentification
TOKEN=$(curl -s -X POST https://ai.4lb.ca/api/auth/login \
  -d "username=admin&password=votremotdepasse" | jq -r '.access_token')

# Chat
curl -X POST https://ai.4lb.ca/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Liste les containers Docker", "model": "auto"}'
```

### WebSocket

```javascript
const ws = new WebSocket('wss://ai.4lb.ca/ws/chat');
ws.onopen = () => {
    ws.send(JSON.stringify({
        message: "Quelle est l'utilisation CPU?",
        model: "auto"
    }));
};
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'complete') {
        console.log(data.answer);
    }
};
```

## Modèles disponibles

| ID | Nom | Description |
|----|-----|-------------|
| auto | AUTO | Sélection automatique |
| qwen-coder | Qwen 2.5 Coder 32B | Code, scripts, debug |
| deepseek-coder | DeepSeek Coder 33B | Algorithmes complexes |
| llama-vision | Llama 3.2 Vision 11B | Analyse d'images |
| qwen-vision | Qwen3 VL 32B | Vision multimodale |
| qwen3-coder-cloud | Qwen3 Coder 480B | Cloud, haute performance |

## Outils disponibles

### Système
- `system_info` - CPU, RAM, disque, GPU
- `execute_command` - Commandes bash (sécurisées)
- `disk_usage` - Analyse espace disque

### Docker
- `docker_status` - État des containers
- `docker_logs` - Logs d'un container
- `docker_restart` - Redémarrer un container

### Fichiers
- `read_file` - Lire un fichier
- `write_file` - Écrire un fichier
- `list_directory` - Lister un répertoire
- `search_files` - Rechercher des fichiers

### Git
- `git_status` - Statut d'un repo
- `git_diff` - Voir les modifications
- `git_log` - Historique des commits
- `git_commit` - Commiter des changements

### Mémoire
- `memory_store` - Mémoriser une information
- `memory_recall` - Rechercher en mémoire
- `memory_stats` - Statistiques mémoire

### Réseau
- `udm_status` - Statut UDM-Pro
- `network_scan` - Scanner les ports
- `web_request` - Requêtes HTTP

## Sécurité

### Authentification

- **JWT** - Tokens d'accès (1h) + refresh tokens (7j)
- **API Keys** - Pour intégrations CI/CD
- **Scopes** - read, write, execute, admin

### Validation

- **Commandes** - Whitelist stricte
- **Chemins** - Répertoires autorisés uniquement
- **Rate Limiting** - 60 req/min par défaut

### Configuration

```bash
# Changer le mot de passe admin
curl -X PUT https://ai.4lb.ca/api/auth/users/admin \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"password": "nouveau-mot-de-passe"}'

# Créer une API key
curl -X POST https://ai.4lb.ca/api/auth/apikeys \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"name": "CI/CD", "scopes": ["read", "execute"]}'
```

## Structure des fichiers

```
ai-orchestrator/
├── backend/
│   ├── main.py           # Application FastAPI
│   ├── security.py       # Validation commandes/chemins
│   ├── auth.py           # Authentification JWT
│   ├── rate_limiter.py   # Rate limiting
│   ├── config.py         # Configuration
│   ├── auto_learn.py     # Auto-apprentissage
│   ├── requirements.txt  # Dépendances Python
│   ├── Dockerfile        # Image Docker
│   └── tests/            # Tests unitaires
├── frontend/
│   └── index.html        # Interface web
├── docs/
│   ├── SECURITY.md       # Guide de sécurité
│   ├── API.md            # Documentation API
│   └── UPGRADE.md        # Guide de migration
├── docker-compose.yml    # Orchestration
└── README.md             # Ce fichier
```

## Tests

```bash
cd backend

# Installer les dépendances de test
pip install pytest pytest-asyncio pytest-cov

# Lancer les tests
pytest tests/ -v

# Avec couverture
pytest tests/ --cov=. --cov-report=html
```

## Documentation

- [Guide de Sécurité](docs/SECURITY.md) - Configuration sécurité
- [Documentation API](docs/API.md) - Endpoints et exemples
- [Guide de Migration](docs/UPGRADE.md) - v2.x vers v3.0

## Changelog

### v3.0.1 (2025-12-15)
- Fix: UnboundLocalError sur conv_id dans WebSocket
- Fix: docker-compose.yml utilise unified-net (au lieu de traefik-net)
- Fix: Suppression de l'attribut version obsolète dans docker-compose

### v3.0.0 (2025-12-14)
- Authentification JWT et API keys
- Rate limiting configurable
- Validation de sécurité des commandes
- Validation de sécurité des chemins
- Audit logging
- CORS restrictif
- Tests unitaires
- Documentation complète

### v2.3.0
- RAG avec ChromaDB
- Templates de projets
- Contexte projet

### v2.2.0
- Planification de tâches
- Auto-correction

### v2.0.0
- Boucle ReAct
- Multi-modèles
- Interface web moderne

## License

MIT

## Contact

- **Web**: https://4lb.ca
- **Email**: admin@4lb.ca
