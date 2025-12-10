#!/bin/bash
# Script d'optimisation système

echo "🚀 Optimisation du système Linux..."

# 1. Nettoyer les caches de packages
echo "📦 Nettoyage des packages..."
sudo apt-get clean
sudo apt-get autoremove -y
sudo apt-get autoclean

# 2. Nettoyer les logs anciens
echo "📝 Nettoyage des logs..."
sudo journalctl --vacuum-time=2d
sudo find /var/log -type f -name "*.log" -mtime +30 -delete

# 3. Nettoyer les fichiers temporaires
echo "🗑️ Nettoyage des fichiers temporaires..."
sudo rm -rf /tmp/*
sudo rm -rf /var/tmp/*

# 4. Optimiser MySQL
echo "💾 Optimisation MySQL..."
sudo mysqlcheck -u root --auto-repair --optimize --all-databases

# 5. Limiter les navigateurs
echo "🌐 Configuration des limites de ressources..."
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# 6. Vérifier l'espace disque
echo "💿 Espace disque actuel:"
df -h

echo "✅ Optimisation terminée!"
