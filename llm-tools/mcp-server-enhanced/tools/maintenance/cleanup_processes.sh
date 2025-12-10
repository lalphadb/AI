#!/bin/bash
# Script de nettoyage des processus pour améliorer les performances

echo "🧹 Nettoyage des processus en cours..."

# Fermer les processus Opera inutiles
echo "Arrêt des processus Opera..."
pkill -f "opera --type=renderer" 2>/dev/null

# Réduire les processus Vivaldi
echo "Nettoyage des processus Vivaldi..."
pkill -f "vivaldi-bin --type=renderer" 2>/dev/null

# Limiter les processus Electron
echo "Optimisation des processus Electron..."
# Ne garde que le processus principal de Claude
for pid in $(pgrep -f "electron --type=zygote"); do
    if [ "$pid" != "15294" ]; then
        kill $pid 2>/dev/null
    fi
done

# Nettoyer le cache système
echo "Libération de la mémoire cache..."
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null 2>&1

# Redémarrer certains services si nécessaire
echo "Vérification des services..."
sudo systemctl restart nginx 2>/dev/null

echo "✅ Nettoyage terminé!"
echo ""
echo "📊 Nouvelles statistiques:"
free -h
echo ""
uptime
