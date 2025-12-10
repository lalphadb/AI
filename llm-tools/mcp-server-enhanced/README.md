# 🚀 MCP Server Enhanced v2.0

Dashboard et système MCP amélioré pour 4lb.ca

## Installation rapide

```bash
cd /home/lalpha/mcp-server-enhanced
sudo bash install.sh
```

## Structure

```
mcp-server-enhanced/
├── core/          # Modules Python améliorés
├── configs/       # Configurations et tasks
├── tools/         # Scripts système
└── logs/          # Logs centralisés
```

## Fonctionnalités

✅ **Cache System** - Cache LRU intelligent  
✅ **Orchestrator** - Workflows automatisés  
✅ **Monitoring** - Surveillance temps réel  
✅ **Auto-Backup** - Sauvegardes automatiques  
✅ **Dashboard** - Interface web moderne  

## Accès

- Dashboard: http://4lb.ca
- Logs: `/home/lalpha/mcp-server-enhanced/logs/`
- Configs: `/home/lalpha/mcp-server-enhanced/configs/`

## SSL (optionnel)

```bash
sudo certbot --nginx -d 4lb.ca -d www.4lb.ca
```

## Support

Documentation complète dans les fichiers sources.
