#!/bin/bash
# 🔧 Setup Self-Improvement Module

set -e

echo "🔧 Configuration du module Self-Improvement..."

# 1. Installer les dépendances Python
echo "📦 Installation des dépendances..."
pip3 install httpx --break-system-packages 2>/dev/null || pip3 install httpx

# 2. Créer le dossier reports
mkdir -p /home/lalpha/projets/ai-tools/self-improvement/reports

# 3. Créer le cron job (analyse quotidienne à 6h du matin)
CRON_JOB="0 6 * * * /usr/bin/python3 /home/lalpha/projets/ai-tools/self-improvement/analyzer.py >> /home/lalpha/projets/ai-tools/self-improvement/cron.log 2>&1"

# Vérifier si le cron existe déjà
if ! crontab -l 2>/dev/null | grep -q "self-improvement"; then
    echo "⏰ Ajout du cron job..."
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "   ✅ Cron configuré : analyse quotidienne à 6h00"
else
    echo "   ℹ️ Cron déjà configuré"
fi

# 4. Tester la connectivité
echo ""
echo "🔍 Test de connectivité..."

# Prometheus
if curl -s http://localhost:9090/-/ready > /dev/null 2>&1; then
    echo "   ✅ Prometheus OK"
else
    echo "   ⚠️ Prometheus non accessible"
fi

# Ollama
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "   ✅ Ollama OK"
else
    echo "   ⚠️ Ollama non accessible"
fi

# Loki
if curl -s http://localhost:3100/ready > /dev/null 2>&1; then
    echo "   ✅ Loki OK"
else
    echo "   ⚠️ Loki non accessible"
fi

echo ""
echo "✅ Configuration terminée!"
echo ""
echo "📋 Commandes disponibles:"
echo "   python3 analyzer.py          # Analyse complète"
echo "   python3 analyzer.py --quick  # Analyse rapide (sans logs)"
echo ""
echo "📁 Rapports: /home/lalpha/projets/ai-tools/self-improvement/reports/"
