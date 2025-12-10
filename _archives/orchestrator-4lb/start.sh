#!/bin/bash
# 🚀 Script de démarrage - Orchestrateur 4LB API

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🎛️ Orchestrateur 4LB - Démarrage API"
echo "========================================"

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 non trouvé!"
    exit 1
fi

# Vérifier les dépendances
echo "📦 Vérification des dépendances..."

if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "📥 Installation de FastAPI..."
    pip3 install fastapi uvicorn pydantic requests --break-system-packages 2>/dev/null || \
    pip3 install fastapi uvicorn pydantic requests
fi

# Créer les dossiers nécessaires
mkdir -p logs backups

# Variables d'environnement
export ORCHESTRATOR_HOST="${ORCHESTRATOR_HOST:-0.0.0.0}"
export ORCHESTRATOR_PORT="${ORCHESTRATOR_PORT:-8888}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

echo ""
echo "🌐 Configuration:"
echo "   Host: $ORCHESTRATOR_HOST"
echo "   Port: $ORCHESTRATOR_PORT"
echo "   Logs: $SCRIPT_DIR/logs/"
echo ""
echo "📚 Documentation: http://localhost:$ORCHESTRATOR_PORT/docs"
echo ""

# Démarrer l'API
echo "🚀 Démarrage du serveur..."
python3 api.py
