#!/bin/bash
# Script de monitoring automatique permanent pour serveur Linux
# Créé par l'assistant autonome StudiosDB

# Configuration
LOG_FILE="/home/studiosdb/monitoring.log"
PID_FILE="/home/studiosdb/.monitoring.pid"
MAX_CPU_PERCENT=80
MAX_MEM_PERCENT=85
MAX_DISK_PERCENT=85
CHECK_INTERVAL=300  # 5 minutes

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Fonction de log
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
    echo -e "$1"
}

# Fonction pour tuer les processus gourmands
kill_heavy_processes() {
    # Tuer les processus qui utilisent plus de 100% CPU
    ps aux | awk '$3 > 100 {print $2}' | while read pid; do
        if [ ! -z "$pid" ]; then
            PROCESS_NAME=$(ps -p $pid -o comm= 2>/dev/null)
            if [[ "$PROCESS_NAME" == *"chatgpt"* ]] || [[ "$PROCESS_NAME" == *"chrome"* ]]; then
                log_message "⚠️ Killing high CPU process: $PROCESS_NAME (PID: $pid)"
                kill -9 $pid 2>/dev/null
            fi
        fi
    done
}

# Fonction pour nettoyer l'espace disque
clean_disk_space() {
    log_message "🧹 Nettoyage automatique de l'espace disque..."
    
    # Nettoyer les logs de plus de 7 jours
    find /var/log -type f -name "*.log" -mtime +7 -exec rm {} \; 2>/dev/null
    
    # Nettoyer les fichiers temporaires
    rm -rf /tmp/* 2>/dev/null
    
    # Nettoyer le cache APT
    apt-get clean 2>/dev/null
    
    # Nettoyer les journaux systemd
    journalctl --vacuum-time=3d 2>/dev/null
}

# Fonction pour optimiser la mémoire
optimize_memory() {
    log_message "💾 Optimisation de la mémoire..."
    
    # Vider les caches système
    sync && echo 3 > /proc/sys/vm/drop_caches 2>/dev/null
    
    # Redémarrer les services gourmands si nécessaire
    MEM_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
    if [ $MEM_USAGE -gt $MAX_MEM_PERCENT ]; then
        log_message "⚠️ Mémoire critique ($MEM_USAGE%). Redémarrage des services..."
        systemctl restart php8.3-fpm 2>/dev/null
        systemctl restart mysql 2>/dev/null
    fi
}

# Fonction pour vérifier NGINX
check_nginx() {
    if ! systemctl is-active --quiet nginx; then
        log_message "🔧 NGINX est inactif. Tentative de redémarrage..."
        
        # Créer les répertoires nécessaires
        mkdir -p /run/nginx 2>/dev/null
        touch /run/nginx.pid 2>/dev/null
        chown -R www-data:www-data /run/nginx 2>/dev/null
        
        # Redémarrer NGINX
        systemctl restart nginx 2>/dev/null
        
        if systemctl is-active --quiet nginx; then
            log_message "✅ NGINX redémarré avec succès"
        else
            log_message "❌ Échec du redémarrage de NGINX"
        fi
    fi
}

# Fonction principale de monitoring
monitor_system() {
    while true; do
        log_message "${GREEN}=== Début du cycle de monitoring ===${NC}"
        
        # 1. Vérifier l'utilisation CPU
        CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print int($2)}' 2>/dev/null)
        if [ ! -z "$CPU_USAGE" ] && [ $CPU_USAGE -gt $MAX_CPU_PERCENT ]; then
            log_message "${YELLOW}⚠️ CPU élevé: ${CPU_USAGE}%${NC}"
            kill_heavy_processes
        else
            log_message "${GREEN}✅ CPU OK: ${CPU_USAGE}%${NC}"
        fi
        
        # 2. Vérifier l'utilisation mémoire
        MEM_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
        if [ $MEM_USAGE -gt $MAX_MEM_PERCENT ]; then
            log_message "${YELLOW}⚠️ Mémoire élevée: ${MEM_USAGE}%${NC}"
            optimize_memory
        else
            log_message "${GREEN}✅ Mémoire OK: ${MEM_USAGE}%${NC}"
        fi
        
        # 3. Vérifier l'espace disque
        DISK_USAGE=$(df / | grep / | awk '{ print int($5)}' | sed 's/%//g')
        if [ $DISK_USAGE -gt $MAX_DISK_PERCENT ]; then
            log_message "${YELLOW}⚠️ Disque presque plein: ${DISK_USAGE}%${NC}"
            clean_disk_space
        else
            log_message "${GREEN}✅ Disque OK: ${DISK_USAGE}%${NC}"
        fi
        
        # 4. Vérifier NGINX
        check_nginx
        
        # 5. Compter les processus Electron/Chrome/Vivaldi
        ELECTRON_COUNT=$(pgrep -c electron 2>/dev/null || echo 0)
        CHROME_COUNT=$(pgrep -c chrome 2>/dev/null || echo 0)
        VIVALDI_COUNT=$(pgrep -c vivaldi 2>/dev/null || echo 0)
        
        if [ $ELECTRON_COUNT -gt 10 ] || [ $CHROME_COUNT -gt 10 ] || [ $VIVALDI_COUNT -gt 10 ]; then
            log_message "${YELLOW}⚠️ Trop de processus navigateur (E:$ELECTRON_COUNT C:$CHROME_COUNT V:$VIVALDI_COUNT)${NC}"
            # Tuer les processus en excès
            pkill -f "electron.*renderer" 2>/dev/null
        fi
        
        log_message "${GREEN}=== Fin du cycle - Attente ${CHECK_INTERVAL}s ===${NC}"
        sleep $CHECK_INTERVAL
    done
}

# Fonction pour démarrer en arrière-plan
start_monitoring() {
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if ps -p $OLD_PID > /dev/null 2>&1; then
            echo "❌ Le monitoring est déjà en cours d'exécution (PID: $OLD_PID)"
            exit 1
        fi
    fi
    
    echo "🚀 Démarrage du monitoring système autonome..."
    echo "📝 Les logs seront enregistrés dans: $LOG_FILE"
    
    # Démarrer en arrière-plan
    nohup bash -c "$(declare -f log_message kill_heavy_processes clean_disk_space optimize_memory check_nginx monitor_system); monitor_system" > /dev/null 2>&1 &
    
    echo $! > "$PID_FILE"
    echo "✅ Monitoring démarré avec PID: $!"
    echo "Pour arrêter: kill $(cat $PID_FILE)"
}

# Fonction pour arrêter le monitoring
stop_monitoring() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID
            rm "$PID_FILE"
            echo "✅ Monitoring arrêté (PID: $PID)"
        else
            echo "⚠️ Le processus n'est pas actif"
            rm "$PID_FILE"
        fi
    else
        echo "❌ Aucun monitoring en cours"
    fi
}

# Gestion des arguments
case "${1:-start}" in
    start)
        start_monitoring
        ;;
    stop)
        stop_monitoring
        ;;
    status)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ps -p $PID > /dev/null 2>&1; then
                echo "✅ Monitoring actif (PID: $PID)"
                tail -n 20 "$LOG_FILE"
            else
                echo "❌ Monitoring inactif"
            fi
        else
            echo "❌ Monitoring non démarré"
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|status}"
        exit 1
        ;;
esac
