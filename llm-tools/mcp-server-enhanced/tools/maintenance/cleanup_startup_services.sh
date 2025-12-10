#!/bin/bash
# Script de nettoyage des services au démarrage
# Créé par StudiosDB Assistant

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🔍 ANALYSE DES SERVICES AU DÉMARRAGE${NC}"
echo "======================================="

# 1. Désactiver les services MCP problématiques
echo -e "\n${RED}1. Désactivation des services MCP défaillants...${NC}"
sudo systemctl stop mcp-local.service 2>/dev/null
sudo systemctl disable mcp-local.service 2>/dev/null
sudo systemctl stop mcp-server.service 2>/dev/null
sudo systemctl disable mcp-server.service 2>/dev/null
sudo systemctl stop mcp-ssh-udm-autonomous.service 2>/dev/null
sudo systemctl disable mcp-ssh-udm-autonomous.service 2>/dev/null
echo "✅ Services MCP désactivés"

# 2. Désactiver keepalived qui échoue
echo -e "\n${RED}2. Désactivation de keepalived...${NC}"
sudo systemctl stop snap.keepalived.daemon.service 2>/dev/null
sudo systemctl disable snap.keepalived.daemon.service 2>/dev/null
sudo snap remove keepalived 2>/dev/null
echo "✅ Keepalived désactivé"

# 3. Corriger le timeout réseau
echo -e "\n${YELLOW}3. Correction du timeout réseau...${NC}"
sudo systemctl disable systemd-networkd-wait-online.service 2>/dev/null
sudo systemctl mask systemd-networkd-wait-online.service 2>/dev/null
echo "✅ Timeout réseau corrigé"

# 4. Désactiver les services Snap inutiles
echo -e "\n${YELLOW}4. Désactivation des services Snap inutiles...${NC}"
SNAP_SERVICES=(
    "snap.canonical-livepatch.canonical-livepatchd.service"
    "snap.prometheus.prometheus.service"
    "snap.wekan.mongodb.service"
    "snap.wekan.wekan.service"
)

for service in "${SNAP_SERVICES[@]}"; do
    sudo systemctl stop "$service" 2>/dev/null
    sudo systemctl disable "$service" 2>/dev/null
    echo "   - $service désactivé"
done

# 5. Désactiver les services de développement non essentiels
echo -e "\n${YELLOW}5. Désactivation des services de développement...${NC}"
DEV_SERVICES=(
    "docker.service"
    "containerd.service"
    "snap.docker.dockerd.service"
    "snap.docker.nvidia-container-toolkit.service"
    "snap.microk8s.daemon-apiserver-kicker.service"
    "snap.microk8s.daemon-apiserver-proxy.service"
    "snap.microk8s.daemon-cluster-agent.service"
    "snap.microk8s.daemon-containerd.service"
    "snap.microk8s.daemon-etcd.service"
    "snap.microk8s.daemon-flanneld.service"
    "snap.microk8s.daemon-k8s-dqlite.service"
    "snap.microk8s.daemon-kubelite.service"
)

echo "Voulez-vous désactiver Docker/Kubernetes? (Économise ~2GB RAM) [y/N]"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    for service in "${DEV_SERVICES[@]}"; do
        sudo systemctl stop "$service" 2>/dev/null
        sudo systemctl disable "$service" 2>/dev/null
        echo "   - $service désactivé"
    done
fi

# 6. Désactiver les services de virtualisation si non utilisés
echo -e "\n${YELLOW}6. Services de virtualisation...${NC}"
echo "Utilisez-vous KVM/libvirt? [y/N]"
read -r response
if [[ ! "$response" =~ ^[Yy]$ ]]; then
    sudo systemctl stop libvirtd.service 2>/dev/null
    sudo systemctl disable libvirtd.service 2>/dev/null
    sudo systemctl stop libvirt-guests.service 2>/dev/null
    sudo systemctl disable libvirt-guests.service 2>/dev/null
    sudo systemctl stop virtlockd.service 2>/dev/null
    sudo systemctl disable virtlockd.service 2>/dev/null
    sudo systemctl stop virtlogd.service 2>/dev/null
    sudo systemctl disable virtlogd.service 2>/dev/null
    echo "✅ Services de virtualisation désactivés"
fi

# 7. Désactiver les timers inutiles
echo -e "\n${YELLOW}7. Désactivation des timers inutiles...${NC}"
TIMERS=(
    "motd-news.timer"
    "ua-timer.timer"
    "update-notifier-download.timer"
    "update-notifier-motd.timer"
    "snapd.snap-repair.timer"
)

for timer in "${TIMERS[@]}"; do
    sudo systemctl stop "$timer" 2>/dev/null
    sudo systemctl disable "$timer" 2>/dev/null
    echo "   - $timer désactivé"
done

# 8. Optimiser le démarrage
echo -e "\n${GREEN}8. Optimisation du démarrage...${NC}"
# Réduire le timeout de systemd
sudo mkdir -p /etc/systemd/system.conf.d/
echo "[Manager]
DefaultTimeoutStartSec=10s
DefaultTimeoutStopSec=10s" | sudo tee /etc/systemd/system.conf.d/timeout.conf

# Désactiver Plymouth si présent
sudo systemctl disable plymouth-quit-wait.service 2>/dev/null
sudo systemctl disable plymouth-start.service 2>/dev/null

# 9. Nettoyer et recharger
echo -e "\n${GREEN}9. Application des changements...${NC}"
sudo systemctl daemon-reload
sudo systemctl reset-failed

# 10. Afficher le résultat
echo -e "\n${GREEN}=== RÉSUMÉ ===${NC}"
echo "Services désactivés avec succès!"
echo ""
echo "Temps de démarrage actuel:"
systemd-analyze time

echo ""
echo "Services les plus lents au démarrage:"
systemd-analyze blame | head -10

echo ""
echo "Services toujours activés:"
systemctl list-unit-files --state=enabled --no-pager | wc -l

echo -e "\n${GREEN}✅ Optimisation terminée!${NC}"
echo "Redémarrez le serveur pour appliquer tous les changements:"
echo "sudo reboot"
