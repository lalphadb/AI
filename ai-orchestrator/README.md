<p align="center">
  <img src="https://img.shields.io/badge/Version-5.2.1-blue?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/Python-3.12-green?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115-teal?style=for-the-badge&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Docker-Ready-blue?style=for-the-badge&logo=docker" alt="Docker">
  <img src="https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge" alt="License">
</p>

# 🤖 AI Orchestrator v5.2.1

**Agent Autonome Intelligent pour l'Infrastructure 4LB.ca**

AI Orchestrator est un agent ReAct (Reason-Act-Observe) avancé conçu pour gérer de manière autonome une infrastructure complète. Il combine la puissance des LLMs locaux via Ollama avec une exécution sécurisée d'outils système, une mémoire sémantique persistante, et des capacités d'auto-guérison.

---

## ✨ Fonctionnalités

| Fonctionnalité | Description |
|----------------|-------------|
| **Boucle ReAct** | Cycle Think → Plan → Act → Observe pour résolution de tâches complexes |
| **Mode Autonome** | Décision et action autonomes avec approche blacklist sécurisée |
| **Multi-Modèles** | Support de 9+ modèles LLM (locaux et cloud) |
| **70 Outils** | Système, Docker, Git, Réseau, Fichiers, Mémoire |
| **Mémoire Sémantique** | ChromaDB pour mémorisation contextuelle persistante |
| **WebSocket Temps Réel** | Streaming de la "pensée" de l'IA en direct |
| **Self-Healing** | Surveillance et réparation automatique |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INFRASTRUCTURE 4LB.CA                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐  │
│   │   Traefik   │────▶│   Nginx     │────▶│   Frontend (HTML)   │  │
│   │   (HTTPS)   │     │  (Static)   │     │   WebSocket Client  │  │
│   └──────┬──────┘     └─────────────┘     └─────────────────────┘  │
│          │                                          │               │
│          ▼                                          ▼               │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                    BACKEND (FastAPI)                         │  │
│   │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐    │  │
│   │   │  Auth   │  │ Engine  │  │ Router  │  │ Rate Limit  │    │  │
│   │   │  JWT    │  │ ReAct   │  │ Query   │  │  + Audit    │    │  │
│   │   └────┬────┘  └────┬────┘  └────┬────┘  └─────────────┘    │  │
│   │        └────────────┴────────────┘                           │  │
│   │                      │                                        │  │
│   │         ┌────────────┴────────────┐                          │  │
│   │         ▼                         ▼                          │  │
│   │   ┌───────────┐           ┌───────────────┐                  │  │
│   │   │   Tools   │           │  LLM Client   │                  │  │
│   │   │  (57+)    │           │   (Ollama)    │                  │  │
│   │   └───────────┘           └───────────────┘                  │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                       DATA LAYER                             │  │
│   │    ┌──────────┐     ┌──────────┐     ┌──────────────────┐   │  │
│   │    │ ChromaDB │     │  SQLite  │     │      Ollama      │   │  │
│   │    │ (Memory) │     │   (DB)   │     │ (Qwen/DeepSeek)  │   │  │
│   │    └──────────┘     └──────────┘     └──────────────────┘   │  │
│   └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Installation Rapide

### Prérequis

- Docker 24.0+ avec Compose V2
- Ollama 0.3.0+ avec modèles (qwen2.5-coder:32b, llama3.2-vision:11b)
- Réseau Docker `unified-net` (192.168.200.0/24)

### Déploiement

```bash
# Via unified-stack (recommandé)
cd /home/lalpha/projets/infrastructure/unified-stack
./stack.sh up

# Vérification
curl -s http://localhost:8001/health | jq
```

### Configuration

```bash
# Copier et éditer le fichier d'environnement
cp backend/.env.example backend/.env
nano backend/.env

# Variables obligatoires
JWT_SECRET_KEY=<openssl rand -base64 32>
ADMIN_PASSWORD=<mot de passe fort>
```

---

## 💻 Utilisation

### Interface Web

Accéder à **https://ai.4lb.ca** pour :
- Chat conversationnel avec streaming temps réel
- Visualisation de la pensée de l'IA (THINK → PLAN → ACTION)
- Sélection du modèle LLM
- Upload de fichiers et images

### API REST

```bash
# Authentification
curl -X POST https://ai.4lb.ca/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# Chat
curl -X POST https://ai.4lb.ca/api/chat \
  -H "Authorization: Bearer <token>" \
  -d '{"message": "Status Docker?"}'
```

### WebSocket

```javascript
const ws = new WebSocket('wss://ai.4lb.ca/ws/chat?token=<JWT>');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
ws.send(JSON.stringify({ message: "Hello" }));
```

---

## 🔧 Modèles LLM

| Clé | Modèle | Usage |
|-----|--------|-------|
| `auto` | Sélection automatique | Défaut recommandé |
| `qwen-coder` | qwen2.5-coder:32b | Code, scripts |
| `deepseek-coder` | deepseek-coder:33b | Algorithmes |
| `llama-vision` | llama3.2-vision:11b | Analyse images |
| `kimi-k2` | Cloud (Moonshot) | Ultra-rapide |
| `gemini-pro` | Cloud (Google) | Tâches complexes |

---

## 🔒 Sécurité

- **Authentification** : JWT avec expiration 1h
- **Rate Limiting** : 100 req/min/IP
- **Blacklist** : 30+ commandes dangereuses interdites
- **Validation** : Chemins et symlinks vérifiés
- **Audit** : Logging complet des actions

Voir [docs/SECURITY.md](docs/SECURITY.md) pour les détails.

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture technique |
| [API.md](docs/API.md) | Référence API complète |
| [SECURITY.md](docs/SECURITY.md) | Guide de sécurité |
| [TOOLS.md](docs/TOOLS.md) | Référence des 57 outils |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Guide de déploiement |
| [CHANGELOG.md](docs/CHANGELOG.md) | Historique des versions |
| [CLAUDE.md](CLAUDE.md) | Instructions Claude Code |

---

## 📊 Métriques

| Métrique | Valeur |
|----------|--------|
| Version | 5.2 |
| LOC Backend | ~8,600 |
| Outils | 57 |
| Modèles LLM | 9 |
| Tests | 15% couverture |

---

## 🛠 Développement

```bash
# Test syntaxe
python3 -m py_compile backend/*.py

# Rebuild Docker
docker compose build ai-orchestrator-backend
docker compose up -d ai-orchestrator-backend

# Logs
docker logs -f ai-orchestrator-backend
```

---

## 📄 Licence

**Propriétaire** - © 2024-2025 4LB.ca - Tous droits réservés.

---

<p align="center">
  <b>AI Orchestrator v5.2.1</b><br>
  Agent Autonome Intelligent pour l'Infrastructure 4LB.ca
</p>
