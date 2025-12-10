# 🧠 Agent 4LB - Agent IA Autonome

> **Statut** : ✅ 100% Fonctionnel  
> **Version** : 1.0.0  
> **Date** : 5 décembre 2025

Agent capable d'exécuter des tâches complexes de manière **100% autonome** en utilisant le pattern ReAct (Reasoning + Acting).

---

## 🎯 Fonctionnement

L'agent utilise une boucle autonome :

```
THINK → ACT → OBSERVE → REPEAT
```

1. **THINK** : Réfléchit à la tâche et planifie
2. **ACT** : Choisit et exécute un outil
3. **OBSERVE** : Analyse le résultat
4. **REPEAT** : Continue ou donne la réponse finale

---

## 🚀 Démarrage

### CLI Interactif
```bash
cd /home/lalpha/projets/ai-tools/agent-4lb
./agent.sh
```

### API REST
```bash
cd /home/lalpha/projets/ai-tools/agent-4lb
./start-api.sh
# API: http://localhost:8889
# Docs: http://localhost:8889/docs
```

---

## 🔧 15 Outils Disponibles

| Catégorie | Outils |
|-----------|--------|
| **Système** | execute_command, read_file, write_file, list_directory, search_files, system_info |
| **Docker** | docker_ps, docker_logs, docker_restart |
| **Git** | git_status, git_commit |
| **Réseau** | check_url |
| **Ollama** | ollama_list, ollama_run |
| **Service** | service_status |

---

## 📁 Structure

```
agent-4lb/
├── core/
│   ├── config.py      # Configuration (LLM, chemins, limites)
│   └── agent.py       # Classe Agent4LB (boucle ReAct)
├── tools/
│   └── system_tools.py # 15 outils disponibles
├── memory/
│   ├── persistent.py  # Mémoire SQLite
│   └── agent_memory.db # Base de données
├── api/
│   └── server.py      # API FastAPI (port 8889)
├── cli.py             # Interface interactive
├── agent.sh           # Script de lancement CLI
├── start-api.sh       # Script de lancement API
└── README.md
```

---

## 📡 API Endpoints

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/` | GET | Info API |
| `/status` | GET | Statut agent + Ollama |
| `/run` | POST | Exécuter une tâche autonome |
| `/chat` | POST | Mode conversation |
| `/history` | GET | Historique des tâches |
| `/memory/stats` | GET | Stats mémoire |
| `/memory/knowledge` | GET/POST | Gestion des connaissances |
| `/sessions` | GET | Sessions actives |
| `/docs` | GET | Documentation Swagger |

---

## ⚙️ Configuration

### Variables d'environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `OLLAMA_HOST` | http://localhost:11434 | Host Ollama |
| `OLLAMA_MODEL` | qwen2.5-coder:32b-instruct-q4_K_M | Modèle LLM |
| `OLLAMA_TEMPERATURE` | 0.1 | Température |
| `API_PORT` | 8889 | Port API |
| `AGENT_MAX_ITERATIONS` | 15 | Limite itérations |
| `ANTHROPIC_API_KEY` | (vide) | Clé Claude (optionnel) |
| `DEFAULT_LLM` | ollama | LLM: ollama ou claude |

### Fichier config.py

```python
# Chemins importants
INFRA_DIR = /home/lalpha/projets/infrastructure/4lb-docker-stack
PROJECTS_DIR = /home/lalpha/projets
SCRIPTS_DIR = /home/lalpha/scripts
MEMORY_DB_PATH = memory/agent_memory.db
```

---

## 💡 Exemples d'utilisation

### Via CLI

```bash
./agent.sh

[TASK] > Liste les conteneurs Docker actifs
[TASK] > Vérifie l'espace disque et les logs de Traefik
[TASK] > Crée un script de backup PostgreSQL
[TASK] > Analyse les performances du serveur
```

### Via API

```bash
# Exécuter une tâche
curl -X POST http://localhost:8889/run \
  -H "Content-Type: application/json" \
  -d '{"task": "Liste les conteneurs Docker actifs"}'

# Mode chat
curl -X POST http://localhost:8889/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Bonjour, comment vas-tu?"}'

# Statut
curl http://localhost:8889/status
```

### Via Python

```python
from core.agent import Agent4LB

agent = Agent4LB()
result = agent.run("Vérifie l'espace disque")
print(result)
```

---

## 💾 Mémoire Persistante

L'agent utilise SQLite avec 4 tables :

| Table | Usage |
|-------|-------|
| `conversations` | Historique des messages par session |
| `tasks` | Tâches exécutées avec résultats |
| `knowledge` | Connaissances apprises |
| `errors` | Erreurs pour auto-amélioration |

---

## 🖥️ Serveur Cible

| Composant | Valeur |
|-----------|--------|
| **Hostname** | lalpha-server-1 |
| **OS** | Ubuntu 25.10 |
| **CPU** | AMD Ryzen 9 7900X (24 cores) |
| **RAM** | 64 GB DDR5 |
| **GPU** | NVIDIA RTX 5070 Ti (16 GB VRAM) |
| **IP** | 10.10.10.46 (VLAN 2) |

---

## 🔗 Voir aussi

- **Orchestrateur 4LB** : `/home/lalpha/projets/ai-tools/orchestrator-4lb/` (automatisation cron)
- **Documentation** : `/home/lalpha/documentation/`
- **MCP Servers** : `/home/lalpha/projets/ai-tools/mcp-servers/`

---

*Créé le 4 décembre 2025 - Mis à jour le 5 décembre 2025*
