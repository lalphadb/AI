#!/bin/bash
# Script de nettoyage final après redémarrage

echo "🧹 Nettoyage final du système..."

# 1. Désactiver les services MCP utilisateur
echo "➡️ Désactivation des services MCP utilisateur..."
systemctl --user disable mcp-fs.service 2>/dev/null
systemctl --user disable mcp-local.service 2>/dev/null
systemctl --user stop mcp-fs.service 2>/dev/null
systemctl --user stop mcp-local.service 2>/dev/null

# 2. Nettoyer les fichiers temporaires
echo "➡️ Nettoyage des fichiers temporaires..."
rm -rf /tmp/* 2>/dev/null
rm -rf /var/tmp/* 2>/dev/null

# 3. Optimiser les bases de données
echo "➡️ Optimisation MySQL..."
sudo mysqlcheck -u root --auto-repair --optimize --all-databases 2>/dev/null

# 4. Afficher l'état final
echo ""
echo "📊 ÉTAT FINAL DU SYSTÈME :"
echo "=========================="
echo "Services en échec: $(systemctl --failed --no-legend | wc -l)"
echo "RAM utilisée: $(free -h | grep Mem | awk '{print $3}')"
echo "RAM disponible: $(free -h | grep Mem | awk '{print $7}')"
echo "Processus actifs: $(ps aux | wc -l)"
echo "Espace disque: $(df -h / | tail -1 | awk '{print $5}')"

echo ""
echo "✅ Optimisation terminée!"
