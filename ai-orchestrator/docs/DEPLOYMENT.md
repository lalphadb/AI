# 🚀 Guide de Déploiement - AI Orchestrator v5.2

## Vue d'Ensemble

Ce guide couvre le déploiement d'AI Orchestrator dans l'infrastructure 4LB.ca via la unified-stack Docker.

---

## Prérequis

### Matériel

| Composant | Minimum | Recommandé |
|-----------|---------|------------|
| CPU | 4 cores | 8+ cores |
| RAM | 16 GB | 32-64 GB |
| GPU | - | NVIDIA 12+ GB VRAM |
| Stockage | 50 GB SSD | 200 GB NVMe |

### Logiciels

```bash
# Versions requises
Docker Engine    >= 24.0
Docker Compose   >= 2.20
Ollama          >= 0.3.0
Ubuntu          >= 22.04
```

### Réseau

- Domaine configuré (ex: ai.4lb.ca)
- Certificat SSL (Let's Encrypt via Traefik)
- Ports 80, 443 ouverts
- Réseau Docker `unified-net`

---

## Installation

### 1. Préparer l'Environnement

```bash
# Créer le réseau Docker si inexistant
docker network create \
  --driver bridge \
  --subnet 192.168.200.0/24 \
  unified-net

# Installer Ollama (sur l'hôte)
curl -fsSL https://ollama.com/install.sh | sh

# Télécharger les modèles essentiels
ollama pull qwen2.5-coder:32b-instruct-q4_K_M
ollama pull llama3.2-vision:11b
ollama pull nomic-embed-text
```

### 2. Configurer les Secrets

```bash
cd /home/lalpha/projets/infrastructure/unified-stack

# Copier le template
cp .env.example .env

# Générer les secrets
JWT_SECRET=$(openssl rand -base64 32)
ADMIN_PASS=$(openssl rand -base64 16)

# Éditer .env
cat >> .env << EOF
JWT_SECRET_KEY=${JWT_SECRET}
ADMIN_PASSWORD=${ADMIN_PASS}
POSTGRES_PASSWORD=$(openssl rand -base64 16)
GRAFANA_PASSWORD=$(openssl rand -base64 16)
CODE_SERVER_PASSWORD=$(openssl rand -base64 16)
WEBUI_SECRET_KEY=$(openssl rand -base64 32)
EOF
```

### 3. Déployer la Stack

```bash
# Démarrer tous les services
./stack.sh up

# Vérifier le statut
./stack.sh status

# Voir les logs
./stack.sh logs ai-orchestrator-backend
```

### 4. Vérifier le Déploiement

```bash
# Santé de l'API
curl -s https://ai.4lb.ca/health | jq

# Test de connexion
curl -X POST https://ai.4lb.ca/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "'${ADMIN_PASS}'"}'
```

---

## Configuration Docker Compose

### Services AI Orchestrator

```yaml
# docker-compose.yml (extrait)
services:
  ai-orchestrator-backend:
    build:
      context: ../ai-tools/ai-orchestrator/backend
      dockerfile: Dockerfile
    container_name: ai-orchestrator-backend
    restart: unless-stopped
    environment:
      - OLLAMA_URL=http://host.docker.internal:11434
      - CHROMADB_HOST=chromadb
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ADMIN_PASSWORD=${ADMIN_PASSWORD}
      - DEBUG=false
    volumes:
      - ai-orchestrator-data:/app/data
    networks:
      - unified-net
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.ai-api.rule=Host(`ai.4lb.ca`) && PathPrefix(`/api`, `/ws`, `/health`, `/tools`)"
      - "traefik.http.routers.ai-api.tls.certresolver=letsencrypt"
      - "traefik.http.services.ai-api.loadbalancer.server.port=8001"

  ai-orchestrator-frontend:
    image: nginx:alpine
    container_name: ai-orchestrator-frontend
    restart: unless-stopped
    volumes:
      - ../ai-tools/ai-orchestrator/frontend:/usr/share/nginx/html:ro
    networks:
      - unified-net
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.ai-frontend.rule=Host(`ai.4lb.ca`)"
      - "traefik.http.routers.ai-frontend.tls.certresolver=letsencrypt"
```

### Volumes

```yaml
volumes:
  ai-orchestrator-data:
    driver: local
```

---

## Traefik Configuration

### Router AI Orchestrator

```yaml
# configs/traefik/dynamic/routers.yml
http:
  routers:
    ai-orchestrator:
      rule: "Host(`ai.4lb.ca`)"
      entryPoints:
        - websecure
      service: ai-orchestrator
      tls:
        certResolver: letsencrypt
      middlewares:
        - security-headers
        - rate-limit
        - geoblock

  services:
    ai-orchestrator:
      loadBalancer:
        servers:
          - url: "http://ai-orchestrator-frontend:80"
```

### Middlewares

```yaml
# configs/traefik/dynamic/middlewares.yml
http:
  middlewares:
    rate-limit:
      rateLimit:
        average: 100
        burst: 200
        
    security-headers:
      headers:
        frameDeny: true
        browserXssFilter: true
        contentTypeNosniff: true
        stsSeconds: 31536000
```

---

## Mise à Jour

### Procédure Standard

```bash
cd /home/lalpha/projets/infrastructure/unified-stack

# 1. Backup
./stack.sh backup

# 2. Pull les changements
cd ../ai-tools/ai-orchestrator
git pull origin main

# 3. Rebuild et redémarrer
cd /home/lalpha/projets/infrastructure/unified-stack
docker compose build ai-orchestrator-backend
docker compose up -d ai-orchestrator-backend

# 4. Vérifier
./stack.sh logs ai-orchestrator-backend
curl -s https://ai.4lb.ca/health
```

### Rollback

```bash
# Restaurer depuis backup
./stack.sh restore <backup_name>

# Ou revenir à une version précédente
cd ../ai-tools/ai-orchestrator
git checkout <commit_hash>
docker compose build ai-orchestrator-backend
docker compose up -d ai-orchestrator-backend
```

---

## Monitoring

### Prometheus Metrics

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'ai-orchestrator'
    static_configs:
      - targets: ['ai-orchestrator-backend:8001']
    metrics_path: '/metrics'
```

### Grafana Dashboard

Importer le dashboard depuis : `configs/grafana/dashboards/ai-orchestrator.json`

### Health Checks

```bash
# Vérifications automatiques
curl -s https://ai.4lb.ca/health | jq '.status'
curl -s https://ai.4lb.ca/api/stats | jq '.tools_count'

# Logs récents
docker logs --tail 100 ai-orchestrator-backend
```

---

## Backup & Restore

### Backup Automatique

```bash
# Configuré dans crontab (3h du matin)
0 3 * * * /home/lalpha/projets/infrastructure/unified-stack/stack.sh backup

# Backup vers Cloudflare R2
0 4 * * * /home/lalpha/projets/ai-tools/backup-system/backup-to-r2.sh
```

### Données à Sauvegarder

| Chemin | Description |
|--------|-------------|
| `ai-orchestrator-data:/app/data` | SQLite DB, sessions |
| `chromadb-data:/chroma/chroma` | Mémoire sémantique |
| `.env` | Secrets (séparément) |

### Restore

```bash
# Depuis backup local
docker run --rm \
  -v ai-orchestrator-data:/data \
  -v /backup:/backup \
  alpine tar xzf /backup/ai-orchestrator-YYYYMMDD.tar.gz -C /data

# Depuis R2
rclone copy r2:backups/ai-orchestrator-latest.tar.gz /tmp/
```

---

## Troubleshooting

### Problèmes Courants

#### Backend ne démarre pas

```bash
# Vérifier les logs
docker logs ai-orchestrator-backend 2>&1 | tail -50

# Vérifier la syntaxe Python
docker exec ai-orchestrator-backend python3 -m py_compile main.py

# Vérifier les dépendances
docker exec ai-orchestrator-backend pip list
```

#### Ollama non accessible

```bash
# Vérifier qu'Ollama tourne
systemctl status ollama

# Tester depuis le conteneur
docker exec ai-orchestrator-backend curl http://host.docker.internal:11434/api/tags
```

#### ChromaDB non accessible

```bash
# Vérifier le conteneur
docker logs chromadb

# Tester la connexion
curl http://localhost:8000/api/v1/heartbeat
```

#### Erreurs SSL

```bash
# Vérifier le certificat
docker exec traefik cat /letsencrypt/acme.json | jq '.letsencrypt.Certificates'

# Forcer le renouvellement
docker exec traefik rm /letsencrypt/acme.json
docker restart traefik
```

### Commandes de Diagnostic

```bash
# État complet
./stack.sh status

# Réseau Docker
docker network inspect unified-net

# Ressources
docker stats --no-stream

# Logs combinés
docker compose logs --tail 50 -f
```

---

## Sécurité Production

### Checklist

- [ ] Secrets générés aléatoirement
- [ ] DEBUG=false
- [ ] AUTH_ENABLED=true
- [ ] HTTPS configuré
- [ ] CrowdSec actif
- [ ] UFW activé
- [ ] Logs rotatés
- [ ] Backups configurés

### Hardening

```bash
# Activer le firewall
sudo ufw enable
sudo ufw allow 80,443/tcp

# Configurer CrowdSec
docker exec crowdsec cscli bouncers add traefik-bouncer

# Rotation des logs
cat > /etc/logrotate.d/docker << EOF
/var/lib/docker/containers/*/*.log {
  daily
  rotate 7
  compress
  missingok
}
EOF
```

---

## Commandes Utiles

```bash
# Gestion Stack
./stack.sh up              # Démarrer
./stack.sh down            # Arrêter
./stack.sh restart         # Redémarrer
./stack.sh status          # Statut
./stack.sh logs [service]  # Logs
./stack.sh test            # Tests santé

# Rebuild spécifique
docker compose build ai-orchestrator-backend
docker compose up -d ai-orchestrator-backend

# Shell dans le conteneur
docker exec -it ai-orchestrator-backend /bin/bash

# Nettoyage
docker system prune -f
docker volume prune -f
```

---

*Guide de Déploiement - AI Orchestrator v5.2*
