#!/bin/bash

# Script de nettoyage des processus inutiles
# ==========================================

echo "🧹 NETTOYAGE INTELLIGENT DES PROCESSUS"
echo "======================================"
echo ""

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher les statistiques
show_stats() {
    echo -e "${YELLOW}📊 État actuel du système:${NC}"
    echo "----------------------------"
    free -h | grep -E "Mem|Swap"
    echo ""
    echo "Load average: $(uptime | awk -F'load average:' '{print $2}')"
    echo ""
}

# Afficher l'état avant nettoyage
echo -e "${YELLOW}AVANT NETTOYAGE:${NC}"
show_stats

# 1. Tuer les processus Electron/Claude Desktop en excès
echo -e "${GREEN}1. Nettoyage des processus Electron/Claude Desktop...${NC}"
ELECTRON_COUNT=$(pgrep -f electron | wc -l)
if [ $ELECTRON_COUNT -gt 5 ]; then
    echo "   ⚠️  $ELECTRON_COUNT processus Electron détectés (limite: 5)"
    pkill -f "electron.*renderer"
    echo "   ✅ Processus renderer Electron tués"
fi

# 2. Limiter les processus Vivaldi
echo -e "${GREEN}2. Optimisation de Vivaldi...${NC}"
VIVALDI_COUNT=$(pgrep -f vivaldi | wc -l)
if [ $VIVALDI_COUNT -gt 10 ]; then
    echo "   ⚠️  $VIVALDI_COUNT processus Vivaldi détectés"
    # Tuer les processus renderer inutiles
    for pid in $(ps aux | grep "vivaldi.*renderer" | awk '{print $2}' | tail -n +10); do
        kill -9 $pid 2>/dev/null
    done
    echo "   ✅ Processus Vivaldi excédentaires tués"
fi

# 3. Limiter les processus Opera
echo -e "${GREEN}3. Optimisation d'Opera...${NC}"
OPERA_COUNT=$(pgrep -f opera | wc -l)
if [ $OPERA_COUNT -gt 10 ]; then
    echo "   ⚠️  $OPERA_COUNT processus Opera détectés"
    # Tuer les processus renderer inutiles
    for pid in $(ps aux | grep "opera.*renderer" | awk '{print $2}' | tail -n +10); do
        kill -9 $pid 2>/dev/null
    done
    echo "   ✅ Processus Opera excédentaires tués"
fi

# 4. Nettoyer les processus zombies
echo -e "${GREEN}4. Nettoyage des processus zombies...${NC}"
ZOMBIES=$(ps aux | awk '$8 ~ /^[Zz]/ { print $2 }')
if [ ! -z "$ZOMBIES" ]; then
    for pid in $ZOMBIES; do
        kill -9 $pid 2>/dev/null
    done
    echo "   ✅ Processus zombies tués"
else
    echo "   ✅ Aucun processus zombie trouvé"
fi

# 5. Nettoyer les processus abandonnés de ChatGPT
echo -e "${GREEN}5. Nettoyage des processus ChatGPT...${NC}"
if pgrep -f chatgpt > /dev/null; then
    pkill -f chatgpt
    echo "   ✅ Processus ChatGPT tués"
else
    echo "   ✅ Aucun processus ChatGPT trouvé"
fi

# 6. Optimiser les processus Snap inutilisés
echo -e "${GREEN}6. Optimisation des services Snap...${NC}"
# Arrêter les snaps non essentiels
SNAPS_TO_CHECK="wekan prometheus"
for snap in $SNAPS_TO_CHECK; do
    if systemctl is-active --quiet snap.$snap.*; then
        echo "   🔄 Arrêt de $snap..."
        sudo systemctl stop snap.$snap.* 2>/dev/null
    fi
done
echo "   ✅ Services Snap optimisés"

# 7. Nettoyer la mémoire cache
echo -e "${GREEN}7. Libération de la mémoire cache...${NC}"
sync
echo 1 | sudo tee /proc/sys/vm/drop_caches > /dev/null
echo "   ✅ Cache mémoire libéré"

# 8. Optimiser MySQL si nécessaire
echo -e "${GREEN}8. Optimisation MySQL...${NC}"
MYSQL_MEM=$(ps aux | grep mysqld | grep -v grep | awk '{print $4}')
if (( $(echo "$MYSQL_MEM > 5" | bc -l) )); then
    echo "   ⚠️  MySQL utilise ${MYSQL_MEM}% de mémoire"
    sudo systemctl restart mysql
    echo "   ✅ MySQL redémarré"
else
    echo "   ✅ MySQL OK (${MYSQL_MEM}% mémoire)"
fi

# 9. Tuer les processus utilisant plus de 10% CPU
echo -e "${GREEN}9. Arrêt des processus gourmands en CPU...${NC}"
HIGH_CPU_PROCS=$(ps aux --sort=-%cpu | awk '$3 > 10 && $11 !~ /^(systemd|kernel|init)/ {print $2, $3, $11}')
if [ ! -z "$HIGH_CPU_PROCS" ]; then
    echo "$HIGH_CPU_PROCS" | while read pid cpu cmd; do
        echo "   ⚠️  PID $pid ($cmd) utilise ${cpu}% CPU"
        # Ne pas tuer les processus système critiques
        if [[ ! "$cmd" =~ (gnome-shell|Xwayland|systemd|kernel) ]]; then
            kill -15 $pid 2>/dev/null
            echo "   ✅ Processus $pid arrêté"
        fi
    done
else
    echo "   ✅ Aucun processus gourmand détecté"
fi

# 10. Nettoyer les processus MCP inutiles
echo -e "${GREEN}10. Optimisation des processus MCP...${NC}"
MCP_COUNT=$(pgrep -f "mcp-server" | wc -l)
if [ $MCP_COUNT -gt 3 ]; then
    echo "   ⚠️  $MCP_COUNT processus MCP détectés"
    pkill -f "mcp-server" --oldest
    echo "   ✅ Anciens processus MCP tués"
fi

# 11. Redémarrer les services essentiels si nécessaire
echo -e "${GREEN}11. Vérification des services essentiels...${NC}"
SERVICES="nginx php8.3-fpm"
for service in $SERVICES; do
    if ! systemctl is-active --quiet $service; then
        echo "   🔄 Redémarrage de $service..."
        sudo systemctl restart $service 2>/dev/null
    else
        echo "   ✅ $service actif"
    fi
done

# Attendre un peu pour que les changements prennent effet
sleep 2

# Afficher l'état après nettoyage
echo ""
echo -e "${YELLOW}APRÈS NETTOYAGE:${NC}"
show_stats

echo ""
echo -e "${GREEN}✅ Nettoyage terminé!${NC}"
echo ""
echo "Conseils pour maintenir les performances:"
echo "- Fermez les onglets inutiles dans les navigateurs"
echo "- Utilisez un seul navigateur à la fois"
echo "- Redémarrez Claude Desktop après ce nettoyage"
echo ""
echo "Pour automatiser ce nettoyage, ajoutez au cron:"
echo "*/30 * * * * /home/studiosdb/clean_processes.sh"
