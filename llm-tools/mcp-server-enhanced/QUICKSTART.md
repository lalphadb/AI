# 🚀 Quick Start Guide - MCP Server Enhanced

## Installation rapide (5 minutes)

### Étape 1: Exécuter les tests
```bash
cd /home/lalpha/mcp-server-enhanced
bash test.sh
```

### Étape 2: Installer (nécessite sudo)
```bash
sudo bash install.sh
```

### Étape 3: Vérifier le dashboard
```bash
curl http://localhost
# Ou ouvrir http://4lb.ca dans un navigateur
```

### Étape 4: Configurer SSL (optionnel)
```bash
sudo certbot --nginx -d 4lb.ca -d www.4lb.ca
```

## Utilisation immédiate

Une fois installé, vous pouvez:

1. **Voir le dashboard**: http://4lb.ca
2. **Utiliser avec Claude**: Les MCP sont automatiquement disponibles
3. **Exécuter des workflows**: 
   ```bash
   python3 -m core.mcp_orchestrator run backup_full
   ```

## Commandes utiles

```bash
# Vérifier le statut
systemctl status nginx
curl -I http://4lb.ca

# Voir les logs
tail -f /var/log/nginx/4lb_access.log
tail -f logs/mcp.log

# Backup manuel
python3 -m core.mcp_orchestrator run backup_full

# Health check
python3 -m core.mcp_orchestrator run health_check
```

## Problèmes courants

**Nginx ne démarre pas?**
```bash
sudo nginx -t
sudo systemctl restart nginx
```

**Dashboard ne saffiche
