#!/bin/bash

# Instructions pour nettoyer les processus manuellement
# =====================================================

echo "📋 GUIDE DE NETTOYAGE MANUEL DES PROCESSUS"
echo "==========================================="
echo ""
echo "Exécutez ces commandes dans votre terminal avec sudo :"
echo ""

# Afficher l'état actuel
echo "1. État actuel du système :"
echo "   free -h"
echo "   df -h"
echo "   top -bn1 | head -20"
echo ""

# Commandes de nettoyage
echo "2. Nettoyage des processus gourmands :"
echo ""
echo "   # Tuer les processus Electron en excès"
echo "   sudo pkill -f 'electron.*renderer'"
echo ""
echo "   # Limiter Vivaldi (garder seulement 10 processus)"
echo "   ps aux | grep 'vivaldi.*renderer' | awk '{print \$2}' | tail -n +10 | xargs -r sudo kill -9"
echo ""
echo "   # Limiter Opera (garder seulement 10 processus)"
echo "   ps aux | grep 'opera.*renderer' | awk '{print \$2}' | tail -n +10 | xargs -r sudo kill -9"
echo ""
echo "   # Tuer ChatGPT"
echo "   sudo pkill -f chatgpt"
echo ""
echo "   # Nettoyer les processus zombies"
echo "   ps aux | awk '\$8 ~ /^[Zz]/ { print \$2 }' | xargs -r sudo kill -9"
echo ""

echo "3. Libération de mémoire :"
echo "   sudo sync"
echo "   echo 1 | sudo tee /proc/sys/vm/drop_caches"
echo ""

echo "4. Redémarrage des services :"
echo "   sudo systemctl restart nginx"
echo "   sudo systemctl restart php8.3-fpm"
echo "   sudo systemctl restart mysql"
echo ""

echo "5. Arrêt des services non essentiels :"
echo "   sudo systemctl stop snap.wekan.*"
echo "   sudo systemctl stop snap.prometheus.*"
echo ""

echo "----------------------------------------"
echo "🚀 COMMANDE TOUT-EN-UN (copier-coller) :"
echo ""
echo 'sudo bash -c "pkill -f electron.*renderer; ps aux | grep vivaldi.*renderer | awk '"'"'{print \$2}'"'"' | tail -n +10 | xargs -r kill -9; ps aux | grep opera.*renderer | awk '"'"'{print \$2}'"'"' | tail -n +10 | xargs -r kill -9; pkill -f chatgpt; sync; echo 1 > /proc/sys/vm/drop_caches; systemctl restart nginx php8.3-fpm"'
echo ""
echo "----------------------------------------"
