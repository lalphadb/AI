# 💾 Backup System v1.0

> **Système de sauvegarde automatique pour infrastructure IA**
> **Date** : 6 décembre 2025

---

## 🎯 Objectif

Sauvegarder automatiquement les éléments critiques de l'infrastructure vers stockage local et optionnellement vers S3-compatible (Cloudflare R2, MinIO, Backblaze B2).

---

## 📦 Éléments Sauvegardés

| Nom | Type | Contenu |
|-----|------|---------|
| docker-compose | Directory | Stack Docker principale |
| ai-orchestrator | Directory | Agent IA v2.0 |
| mcp-servers | Directory | 33 outils MCP |
| documentation | Directory | Toute la doc |
| scripts | Directory | Scripts système |
| postgres | Database | Toutes les bases PostgreSQL |
| self-improvement-reports | Directory | Rapports d'analyse |

---

## 🚀 Utilisation

### Backup local
```bash
python3 backup.py
```

### Backup avec upload S3
```bash
python3 backup.py --upload
```

### Backup avec nettoyage des anciens
```bash
python3 backup.py --cleanup
```

### Complet
```bash
python3 backup.py --upload --cleanup
```

---

## ⚙️ Configuration S3

### Option 1 : Cloudflare R2

1. Créer un bucket R2 dans Cloudflare Dashboard
2. Générer des clés API (Access Key ID + Secret)
3. Configurer les variables :

```bash
export S3_ENDPOINT="https://xxx.r2.cloudflarestorage.com"
export S3_ACCESS_KEY="votre_access_key"
export S3_SECRET_KEY="votre_secret_key"
export S3_BUCKET="lalpha-backups"
```

### Option 2 : rclone (recommandé)

```bash
# Installer rclone
sudo apt install rclone

# Configurer
rclone config
# Choisir: n (new remote)
# Name: s3
# Type: s3
# Provider: Cloudflare (ou autre)
# Suivre les instructions...

# Tester
rclone ls s3:lalpha-backups
```

---

## ⏰ Automatisation (Cron)

```bash
# Backup quotidien à 3h du matin
0 3 * * * /usr/bin/python3 /home/lalpha/projets/ai-tools/backup-system/backup.py --cleanup >> /home/lalpha/projets/ai-tools/backup-system/cron.log 2>&1
```

---

## 📁 Structure

```
backup-system/
├── backup.py           # Script principal
├── README.md           # Cette doc
├── cron.log           # Logs d'exécution
└── local/             # Backups locaux
    ├── docker-compose_YYYYMMDD_HHMMSS.tar.gz
    ├── ai-orchestrator_YYYYMMDD_HHMMSS.tar.gz
    ├── postgres_YYYYMMDD_HHMMSS.sql.gz
    └── latest_backup.json
```

---

## 📊 Format du Résumé

```json
{
    "timestamp": "2025-12-06T...",
    "backups": [
        {"name": "docker-compose_...", "size_mb": 1.5, "path": "..."}
    ],
    "total_size_mb": 15.2
}
```

---

## 🔐 Restauration

### Répertoire
```bash
tar -xzf backup-system/local/docker-compose_YYYYMMDD.tar.gz -C /destination/
```

### PostgreSQL
```bash
gunzip -c backup-system/local/postgres_YYYYMMDD.sql.gz | docker exec -i postgres psql -U postgres
```

---

*Module créé le 6 décembre 2025*
