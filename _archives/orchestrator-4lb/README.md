# 🎛️ Orchestrateur 4LB

> Infrastructure IA Self-Improving pour lalpha-server-1

## 📊 Vue d'ensemble

L'Orchestrateur 4LB est un système de gestion intelligente d'infrastructure qui utilise l'IA locale (Ollama) pour s'auto-améliorer.

### ✨ Fonctionnalités

- **22 Outils** répartis en 4 modules
- **Auto-amélioration** avec analyse IA des logs
- **GitOps** pour la gestion versionnée
- **Backups automatisés** (PostgreSQL, configs, Ollama)
- **API REST** et **CLI interactif**
- **Détection d'anomalies** avec métriques système

## 🚀 Démarrage rapide

### Option 1: CLI Interactif

```bash
./cli.sh
```

### Option 2: API REST

```bash
./start.sh
# Ouvrir http://localhost:8888/docs
```

### Option 3: Docker (Production)

```bash
docker compose up -d
# Accessible via https://orchestrator.4lb.ca
```

## 📦 Modules et Outils

### 🔧 Base (9 outils)
| Outil | Description |
|-------|-------------|
| `read_file` | Lire un fichier |
| `write_file` | Écrire dans un fichier (avec backup) |
| `propose_diff` | Proposer des modifications (safe mode) |
| `apply_diff` | Appliquer une proposition |
| `run_command` | Exécuter une commande shell |
| `list_directory` | Lister un répertoire |
| `file_exists` | Vérifier l'existence d'un fichier |
| `get_system_info` | Informations système |
| `docker_status` | État des conteneurs Docker |

### 🔄 GitOps (6 outils)
| Outil | Description |
|-------|-------------|
| `gitops_init` | Initialiser Git sur un projet |
| `gitops_status` | Voir le statut Git |
| `gitops_commit` | Commit les changements |
| `gitops_rollback` | Revenir à une version précédente |
| `gitops_setup_hooks` | Configurer les hooks auto-deploy |
| `gitops_log` | Voir l'historique des commits |

### 💾 Backup (5 outils)
| Outil | Description |
|-------|-------------|
| `backup_postgres` | Sauvegarde PostgreSQL |
| `backup_configs` | Sauvegarde des configurations |
| `backup_ollama_models` | Liste des modèles Ollama |
| `backup_full` | Sauvegarde complète |
| `backup_s3` | Upload vers S3/MinIO |

### 🧠 Self-Improve (3 outils)
| Outil | Description |
|-------|-------------|
| `self_improve_analyze_logs` | Analyse des logs avec Ollama |
| `self_improve_anomalies` | Détection d'anomalies |
| `self_improve_suggestions` | Suggestions d'optimisation |

## 🕐 Automatisation (Cron)

Ajouter au crontab (`crontab -e`):

```cron
# Analyse quotidienne à 6h00
0 6 * * * cd /home/lalpha/projets/ai-tools/orchestrator && python3 scripts/daily_analysis.py >> logs/cron.log 2>&1

# Backup hebdomadaire dimanche à 2h00
0 2 * * 0 cd /home/lalpha/projets/ai-tools/orchestrator && python3 scripts/weekly_backup.py >> logs/cron.log 2>&1
```

## 📡 API REST

### Endpoints principaux

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/` | Info API |
| GET | `/health` | Health check |
| GET | `/tools` | Liste des outils |
| POST | `/execute` | Exécuter un outil |
| GET | `/metrics` | Métriques système |
| GET | `/backups` | Liste des backups |
| POST | `/backup` | Créer un backup |
| GET | `/gitops/status` | Statut GitOps |
| POST | `/gitops/commit` | Commit GitOps |
| GET | `/analyze` | Analyser le système |
| GET | `/suggestions` | Suggestions IA |

### Exemples d'utilisation

```bash
# Status
curl http://localhost:8888/health

# Docker status
curl -X POST http://localhost:8888/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "docker_status"}'

# Analyse IA
curl http://localhost:8888/analyze

# Backup
curl -X POST http://localhost:8888/backup \
  -H "Content-Type: application/json" \
  -d '{"type": "full"}'
```

## 🛡️ Sécurité

### Chemins protégés

Les fichiers suivants nécessitent `propose_diff()` :
- `/etc/*`
- `/root/*`
- `/var/lib/docker/*`
- `docker-compose.yml`
- `traefik/*`

### Commandes autorisées

Seules certaines commandes sont autorisées :
- `docker`, `docker-compose`
- `systemctl`, `journalctl`
- `ls`, `cat`, `grep`, `find`, `df`, `du`
- `curl`, `wget`
- `git`, `npm`, `node`, `python3`
- `ollama`, `nvidia-smi`

## ⚙️ Configuration

### Variables d'environnement

```bash
# Serveur
ORCHESTRATOR_HOST=0.0.0.0
ORCHESTRATOR_PORT=8888

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:32b

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres

# S3 (optionnel)
S3_ENABLED=false
S3_ENDPOINT=https://s3.amazonaws.com
S3_BUCKET=4lb-backups
S3_ACCESS_KEY=
S3_SECRET_KEY=
```

## 📁 Structure

```
orchestrator-4lb/
├── api.py              # API REST FastAPI
├── cli.py              # CLI interactif
├── start.sh            # Script démarrage API
├── cli.sh              # Script démarrage CLI
├── config/
│   └── settings.py     # Configuration
├── modules/
│   ├── base.py         # Outils fondamentaux
│   ├── gitops.py       # GitOps
│   ├── backup.py       # Backup
│   └── self_improve.py # Auto-amélioration
├── scripts/
│   ├── daily_analysis.py   # Cron quotidien
│   └── weekly_backup.py    # Cron hebdomadaire
├── logs/               # Logs et rapports
├── backups/            # Sauvegardes
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 🐛 Dépannage

### Ollama non connecté

```bash
# Vérifier Ollama
curl http://localhost:11434/api/tags

# Redémarrer si nécessaire
sudo systemctl restart ollama
```

### Docker non accessible

```bash
# Vérifier les permissions
sudo usermod -aG docker $USER
# Puis déconnexion/reconnexion
```

### API ne démarre pas

```bash
# Vérifier les dépendances
pip3 install -r requirements.txt

# Logs
python3 api.py
```

## 📜 Licence

Projet privé - 4lb.ca

---

**Version**: 1.0.0  
**Créé le**: $(date +%Y-%m-%d)  
**Auteur**: Claude + Lalpha
