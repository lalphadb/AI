# Infrastructure 4LB.ca - Documentation Complete

Documentation de l'infrastructure Docker et des sites web geres par l'AI Orchestrator.

## Vue d'Ensemble

```
+------------------+     +------------------+     +------------------+
|   Internet       |     |    Traefik       |     |   Services       |
|   (*.4lb.ca)     |---->|   (Reverse Proxy)|---->|   Docker         |
+------------------+     +------------------+     +------------------+
        |                        |                        |
   HTTPS/443                  :80/:443              Reseau unified-net
```

## Containers Docker

### Services Core

| Container | Image | Status | Ports | Description |
|-----------|-------|--------|-------|-------------|
| `traefik` | traefik:v3.6 | Healthy | 80, 443, 8080 | Reverse proxy avec Let's Encrypt |
| `postgres` | postgres:16-alpine | Healthy | 5432 | Base de donnees PostgreSQL |
| `redis` | redis:7-alpine | Healthy | 6379 | Cache et sessions |
| `chromadb` | chromadb | Healthy | 8000 | Base de donnees vectorielle |
| `crowdsec` | crowdsecurity/crowdsec | Healthy | - | Protection DDoS/WAF |

### AI et LLM

| Container | Image | Status | Description |
|-----------|-------|--------|-------------|
| `ai-orchestrator-backend` | ai-orchestrator-backend | Healthy | API FastAPI ReAct Engine |
| `ai-orchestrator-frontend` | nginx:alpine | Up | Interface web |
| `open-webui` | open-webui | Healthy | Interface Ollama alternative |

### Monitoring

| Container | Image | Status | Description |
|-----------|-------|--------|-------------|
| `prometheus` | prometheus | Up | Collecte de metriques |
| `grafana` | grafana | Up | Dashboards et alertes |
| `cadvisor` | cadvisor | Healthy | Metriques Docker |
| `node-exporter` | node-exporter | Up | Metriques systeme |

### Applications Web

| Container | Image | Status | Description |
|-----------|-------|--------|-------------|
| `jsr-dev` | jsr-dev | Up | Site JSR developpement |
| `jsr-solutions` | jsr-solutions | Up | Site JSR Solutions dev |
| `jsr-solutions-prod` | jsr-solutions-frontend | Up | Site JSR Solutions prod |
| `code-server` | code-server | Up | VS Code dans le navigateur |

## Domaines et Routes

### Domaines 4lb.ca

| Domaine | Container | Description |
|---------|-----------|-------------|
| `ai.4lb.ca` | ai-orchestrator | AI Orchestrator - Interface principale |
| `llm.4lb.ca` | open-webui | Open WebUI pour Ollama |
| `code.4lb.ca` | code-server | VS Code Server |
| `grafana.4lb.ca` | grafana | Dashboards monitoring |
| `prometheus.4lb.ca` | prometheus | Interface Prometheus |
| `traefik.4lb.ca` | traefik | Dashboard Traefik |
| `jsr.4lb.ca` | jsr-dev | Site JSR developpement |

### Domaines Clients

| Domaine | Container | Description |
|---------|-----------|-------------|
| `jsr-solutions.ca` | jsr-solutions | Site JSR Solutions |
| `www.jsr-solutions.ca` | jsr-solutions | Alias www |

## Architecture Reseau

```
Reseau: unified-net (bridge)

Internet
    |
    v
[Traefik:443] --> Terminaison SSL (Let's Encrypt)
    |
    +---> [ai-orchestrator-backend:8001]
    +---> [ai-orchestrator-frontend:80]
    +---> [open-webui:8080]
    +---> [grafana:3000]
    +---> [prometheus:9090]
    +---> [code-server:8443]
    +---> [jsr-dev:80]
    +---> [jsr-solutions:80]

Interne (non expose):
    +---> [postgres:5432]
    +---> [redis:6379]
    +---> [chromadb:8000]
    +---> [crowdsec]
```

## Volumes Persistants

| Volume | Container | Chemin | Usage |
|--------|-----------|--------|-------|
| postgres_data | postgres | /var/lib/postgresql/data | Donnees PostgreSQL |
| redis_data | redis | /data | Donnees Redis |
| chromadb_data | chromadb | /chroma/chroma | Vecteurs ChromaDB |
| traefik_certs | traefik | /letsencrypt | Certificats SSL |
| grafana_data | grafana | /var/lib/grafana | Dashboards Grafana |
| prometheus_data | prometheus | /prometheus | Metriques historiques |

## Securite

### Traefik (Reverse Proxy)

- **SSL/TLS**: Let's Encrypt automatique
- **Headers securite**: HSTS, X-Frame-Options, CSP
- **Rate limiting**: Via CrowdSec
- **Authentification**: BasicAuth sur endpoints sensibles

### CrowdSec

- Detection de patterns d'attaque
- Blocage automatique des IPs malveillantes
- Partage communautaire de reputation IP

### Backend AI Orchestrator

- **JWT**: Tokens signes avec expiration 1h
- **Rate Limiting**: 60 req/min par defaut
- **Validation commandes**: Blacklist de commandes dangereuses
- **Audit Logging**: Toutes les actions tracees

## Maintenance

### Commandes Utiles

```bash
# Status de tous les containers
docker ps -a

# Logs d'un container
docker logs -f ai-orchestrator-backend

# Redemarrer un service
docker compose restart ai-orchestrator-backend

# Mettre a jour un container
docker compose pull && docker compose up -d

# Nettoyage des images non utilisees
docker image prune -a
```

### Backups

Les backups automatiques sont configures via cron:
- **Base de donnees**: pg_dump quotidien
- **Volumes**: Snapshot tar.gz
- **Retention**: 7 jours local, 30 jours remote

Voir `/home/lalpha/projets/ai-tools/backup-system/` pour la configuration.

### Monitoring

- **Grafana**: `grafana.4lb.ca` - Dashboards de performance
- **Prometheus**: `prometheus.4lb.ca` - Metriques brutes
- **Alertes**: Email sur seuils critiques (CPU > 90%, Disk > 90%)

## Projets Geres

### Clients

| Projet | Chemin | Description |
|--------|--------|-------------|
| JSR | `/home/lalpha/projets/clients/jsr/` | Site web JSR |
| JSR Solutions | `/home/lalpha/projets/clients/jsr/JSR-solutions/` | Site JSR Solutions |
| Toilettage | `/home/lalpha/projets/clients/toilettage/` | Application toilettage |

### Applications Internes

| Projet | Chemin | Description |
|--------|--------|-------------|
| AI Orchestrator | `/home/lalpha/projets/ai-tools/ai-orchestrator/` | Agent IA autonome |
| Backup System | `/home/lalpha/projets/ai-tools/backup-system/` | Backups automatiques |
| Self-Improvement | `/home/lalpha/projets/ai-tools/self-improvement/` | Auto-amelioration IA |

---

**Derniere mise a jour**: 2025-12-28
**Genere par**: AI Orchestrator v5.1
