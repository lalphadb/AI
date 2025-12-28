# Architecture AI Orchestrator v5.1

## Vue d'ensemble

L'AI Orchestrator est un **agent autonome intelligent** concu pour gerer l'infrastructure de 4LB.ca. Il combine la puissance des LLMs (via Ollama) avec une execution d'outils systeme securisee, une memoire semantique persistante (ChromaDB), et un systeme d'auto-guerison.

```
                                   +---------------------------+
                                   |      Frontend (Nginx)     |
                                   |    - Interface React-like |
                                   |    - WebSocket Client     |
                                   |    - TailwindCSS          |
                                   +-------------+-------------+
                                                 |
                                                 | HTTPS/WSS
                                                 v
+------------------+              +---------------------------+              +------------------+
|                  |   REST/WS   |                           |   HTTP       |                  |
|    Traefik       +<----------->+   Backend FastAPI         +<------------>+   Ollama LLM     |
|   (Reverse       |             |                           |              |   (10.10.10.46)  |
|    Proxy)        |             |   - Boucle ReAct          |              |                  |
|                  |             |   - Authentification JWT  |              +------------------+
+------------------+             |   - Rate Limiting         |
                                 |   - Modules Tools v5.0    |              +------------------+
                                 |   - Self-Healing Service  |   HTTP       |                  |
                                 |                           +<------------>+   ChromaDB       |
                                 +-------------+-------------+              |   (Memoire)      |
                                               |                            |                  |
                                               | SSH/Docker                 +------------------+
                                               v
                                 +---------------------------+
                                 |      Hote (10.10.10.46)   |
                                 |   - Commandes systeme     |
                                 |   - Services systemd      |
                                 |   - Docker daemon         |
                                 +---------------------------+
```

---

## Structure du Projet

```
ai-orchestrator/
+-- backend/                     # Coeur du systeme
|   +-- main.py                  # Point d'entree FastAPI (1200+ lignes)
|   +-- engine.py                # Moteur ReAct v5.1
|   +-- config.py                # Configuration centralisee (Pydantic)
|   +-- security.py              # Validation commandes (blacklist)
|   +-- auth.py                  # Authentification JWT + API Keys
|   +-- rate_limiter.py          # Protection anti-abus
|   +-- auto_learn.py            # Auto-apprentissage semantique
|   +-- prompts.py               # Prompts systeme
|   +-- dynamic_context.py       # Contexte dynamique
|   +--
|   +-- tools/                   # Modules d'outils v5.0
|   |   +-- __init__.py          # Chargement dynamique + decorateur @register_tool
|   |   +-- system_tools.py      # Commandes systeme, SSH vers hote
|   |   +-- docker_tools.py      # Gestion Docker
|   |   +-- file_tools.py        # Lecture/ecriture fichiers
|   |   +-- git_tools.py         # Operations Git
|   |   +-- memory_tools.py      # Memoire semantique ChromaDB
|   |   +-- ai_tools.py          # Outils IA
|   |   +-- network_tools.py     # Outils reseau
|   |   +-- meta_tools.py        # Meta-outils
|   |
|   +-- services/                # Services autonomes
|   |   +-- self_healing.py      # Auto-guerison systeme
|   |
|   +-- utils/                   # Utilitaires
|   |   +-- async_subprocess.py  # Execution async securisee
|   |
|   +-- tests/                   # Tests unitaires
|   |   +-- test_auth.py
|   |   +-- test_security.py
|   |   +-- test_rate_limiter.py
|   |
|   +-- data/                    # Donnees persistantes
|   |   +-- orchestrator.db      # SQLite conversations
|   |   +-- auth.db              # SQLite utilisateurs
|   |   +-- uploads/             # Fichiers uploades
|   |
|   +-- Dockerfile
|   +-- requirements.txt
|
+-- frontend/
|   +-- index.html               # SPA complete (Single File)
|
+-- docs/                        # Documentation
|   +-- ARCHITECTURE.md          # Ce fichier
|   +-- API.md                   # Reference API
|   +-- SECURITY.md              # Guide securite
|   +-- UPGRADE.md               # Guide migration
|   +-- TOOLS.md                 # Documentation outils
|
+-- docker-compose.yml           # Orchestration Docker
+-- nginx.conf                   # Configuration Nginx
+-- README.md                    # Introduction projet
```

---

## Composants Principaux

### 1. Moteur ReAct (engine.py)

Le coeur de l'intelligence de l'agent. Implemente la boucle **Reasoning + Acting**:

```
UTILISATEUR: "Quel est l'etat des containers Docker?"
    |
    v
+-------------------+
| 1. THINK          |  "Je dois verifier les containers Docker"
+-------------------+
    |
    v
+-------------------+
| 2. ACT            |  docker_status()
+-------------------+
    |
    v
+-------------------+
| 3. OBSERVE        |  "15 containers actifs..."
+-------------------+
    |
    v
+-------------------+
| 4. THINK          |  "J'ai les infos, je peux repondre"
+-------------------+
    |
    v
+-------------------+
| 5. RESPOND        |  final_answer("Voici les containers...")
+-------------------+
```

**Parametres cles:**
- `MAX_ITERATIONS = 15` - Iterations max par requete
- `LLM_TIMEOUT = 300s` - Timeout par appel LLM
- `DEFAULT_MODEL = qwen3-coder:480b-cloud`

### 2. Systeme d'Outils (tools/)

Architecture modulaire avec chargement dynamique:

```python
# Decorateur pour enregistrer un outil
@register_tool("docker_status", description="Liste les containers Docker")
async def docker_status(params: dict) -> str:
    output, code = await run_command_async("docker ps -a ...")
    return f"Conteneurs Docker:\n{output}"
```

**Rechargement a chaud:**
```python
from tools import reload_tools
reload_tools()  # Recharge tous les modules *_tools.py
```

### 3. Securite (security.py)

**Mode Autonome v5.0** - Approche blacklist au lieu de whitelist:

```python
# Commandes INTERDITES (blacklist)
FORBIDDEN_COMMANDS = {
    "mkfs", "fdisk", "parted", "dd",      # Formatage disque
    "insmod", "rmmod", "modprobe",         # Modules kernel
}

# Patterns dangereux
FORBIDDEN_PATTERNS = [
    r"rm\s+-rf\s+/\s*$",      # rm -rf /
    r":\(\)\{\s*:\|:&\s*\};:", # Fork bomb
]
```

### 4. Authentification (auth.py)

Systeme JWT complet:

```
+-------------------+     +-------------------+     +-------------------+
|   Login           | --> |   Access Token    | --> |   API Request     |
|   (username/pwd)  |     |   (1h validity)   |     |   (Bearer token)  |
+-------------------+     +-------------------+     +-------------------+
                                    |
                                    v
                          +-------------------+
                          |   Refresh Token   |
                          |   (7j validity)   |
                          +-------------------+
```

**Scopes disponibles:**
- `read` - Lecture seule
- `write` - Ecriture fichiers
- `execute` - Execution commandes
- `admin` - Tous les droits

### 5. Auto-Apprentissage (auto_learn.py)

Extraction automatique de faits:

```python
FACT_PATTERNS = [
    (r"je suis (.+?)\.", "user_fact"),
    (r"je travaille sur (.+?)\.", "project"),
    (r"je prefere (.+?)\.", "preference"),
]
```

**Flux:**
1. Message utilisateur recu
2. Extraction des faits via regex
3. Stockage dans ChromaDB
4. Rappel semantique lors des prochaines requetes

### 6. Self-Healing Service (services/self_healing.py)

Service autonome de surveillance:

```
Toutes les 5 minutes:
    |
    +-> Verifier espace disque (> 90%?)
    +-> Verifier Docker accessible?
    +-> Verifier charge systeme (< 4.0?)
    |
    Si probleme detecte:
        |
        +-> Lancer react_loop() avec prompt de reparation
        +-> L'IA analyse et corrige automatiquement
```

---

## Flux de Donnees

### Requete Chat Complete

```
1. Client WebSocket envoie message
   {"message": "Liste les containers", "model": "auto"}
        |
        v
2. Backend recoit via /ws/chat
        |
        v
3. Authentification JWT verifiee
        |
        v
4. Auto-apprentissage: extraction faits du message
        |
        v
5. Contexte memoire: recherche semantique ChromaDB
        |
        v
6. react_loop() demarre
   +-- Iteration 1: LLM reflechit
   +-- Iteration 2: LLM appelle docker_status()
   +-- Iteration 3: LLM analyse resultat
   +-- Iteration 4: final_answer()
        |
        v
7. Reponse envoyee via WebSocket
   {"type": "complete", "answer": "..."}
        |
        v
8. Message sauvegarde en DB
        |
        v
9. Resume conversation sauvegarde (deconnexion)
```

---

## Base de Donnees

### SQLite - orchestrator.db

```sql
-- Conversations
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    title TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Messages
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    conversation_id TEXT,
    role TEXT,           -- 'user' ou 'assistant'
    content TEXT,
    model_used TEXT,
    created_at TIMESTAMP
);

-- Memoire simple (key-value)
CREATE TABLE memory (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP
);

-- Fichiers uploades
CREATE TABLE uploads (
    id TEXT PRIMARY KEY,
    filename TEXT,
    filepath TEXT,
    filetype TEXT,
    filesize INTEGER,
    conversation_id TEXT,
    created_at TIMESTAMP
);
```

### SQLite - auth.db

```sql
-- Utilisateurs
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    hashed_password TEXT,
    email TEXT,
    is_admin BOOLEAN,
    scopes TEXT,  -- JSON array
    disabled BOOLEAN
);

-- Sessions (refresh tokens)
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    refresh_token_hash TEXT,
    expires_at TIMESTAMP
);

-- API Keys
CREATE TABLE api_keys (
    id INTEGER PRIMARY KEY,
    key_hash TEXT,
    name TEXT,
    user_id INTEGER,
    scopes TEXT,
    expires_at TIMESTAMP
);

-- Tentatives login (rate limiting)
CREATE TABLE login_attempts (
    id INTEGER PRIMARY KEY,
    username TEXT,
    ip_address TEXT,
    success BOOLEAN,
    created_at TIMESTAMP
);
```

### ChromaDB - Memoire Semantique

```
Collection: ai_orchestrator_memory

Documents:
+--------------------+------------------------+-------------------+
| ID                 | Document               | Metadata          |
+--------------------+------------------------+-------------------+
| auto_user_fact_123 | "developpeur Python"   | category: user    |
| auto_project_456   | "ai-orchestrator"      | category: project |
| conv_abc123        | "conversation summary" | type: summary     |
| solution_def789    | "bug fix: restart"     | type: solution    |
+--------------------+------------------------+-------------------+
```

---

## Communication Inter-Services

### Backend <-> Hote (SSH)

```python
# system_tools.py
HOST = os.getenv("HOST_IP", "host.docker.internal")
USER = os.getenv("HOST_USER", "lalpha")
KEY = "/root/.ssh/id_ed25519"

SSH = f"ssh -o StrictHostKeyChecking=no -i {KEY} {USER}@{HOST}"

# Commandes necessitant SSH vers hote
HOST_CMDS = {"systemctl", "service", "journalctl", "apt", "nvidia-smi", ...}
```

### Backend <-> Ollama

```python
# Appel LLM
async with httpx.AsyncClient(timeout=300) as client:
    response = await client.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": "qwen3-coder:480b-cloud",
            "messages": [...],
            "stream": False,
            "options": {"temperature": 0.3}
        }
    )
```

### Backend <-> ChromaDB

```python
# Stockage memoire
collection.upsert(
    ids=["fact_123"],
    documents=["L'utilisateur est developpeur"],
    metadatas=[{"category": "user_fact"}]
)

# Recherche semantique
results = collection.query(
    query_texts=["competences utilisateur"],
    n_results=5
)
```

---

## Deploiement Docker

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    environment:
      - OLLAMA_URL=http://host.docker.internal:11434
      - CHROMADB_HOST=chromadb
      - AUTONOMOUS_MODE=true
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # Acces Docker
      - /home/lalpha:/home/lalpha                   # Acces fichiers
      - ~/.ssh/id_ed25519:/root/.ssh/id_ed25519:ro # Cle SSH
    networks:
      - unified-net

  frontend:
    image: nginx:alpine
    volumes:
      - ./frontend:/usr/share/nginx/html:ro
    depends_on:
      - backend

networks:
  unified-net:
    external: true
```

---

## Modeles LLM Disponibles

| ID | Modele | Usage |
|----|--------|-------|
| `auto` | Selection automatique | Recommande |
| `qwen-coder` | Qwen 2.5 Coder 32B | Code, debug |
| `deepseek-coder` | DeepSeek Coder 33B | Algorithmes |
| `llama-vision` | Llama 3.2 Vision 11B | Analyse images |
| `qwen-vision` | Qwen3 VL 32B | Vision avancee |
| `qwen3-coder-cloud` | Qwen3 480B (cloud) | Default |
| `gemini-pro` | Gemini 3 Pro | Cloud Google |

---

## Points Cles de Securite

1. **Zero shell=True** - Toutes les commandes via `asyncio.create_subprocess_exec()`
2. **Blacklist** - Commandes dangereuses bloquees
3. **Sanitization** - Noms containers Docker valides
4. **JWT** - Tokens signes avec expiration
5. **Rate Limiting** - 60 req/min par defaut
6. **Audit Log** - Toutes les actions tracees
7. **CSP Headers** - Protection XSS frontend

---

## Performance

- **Timeout LLM**: 300s pour requetes complexes
- **Max iterations**: 15 par conversation
- **Rate limit**: 60 req/min (configurable)
- **Refresh interval stats**: 5s
- **Self-healing check**: 5 min

---

## Ameliorations v5.0 -> v5.1

1. **Engine optimise** - Meilleur extraction final_answer
2. **Tools modulaires** - Chargement dynamique
3. **Mode Autonome** - Blacklist au lieu de whitelist
4. **SSH transparent** - Commandes hote via SSH
5. **Self-Healing** - Surveillance et reparation auto
6. **Frontend v4.1** - Refresh token, reconnexion auto
