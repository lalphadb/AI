#!/bin/bash
# 🖥️ CLI Interactif - Orchestrateur 4LB

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 non trouvé!"
    exit 1
fi

# Vérifier les dépendances minimales
if ! python3 -c "import requests" 2>/dev/null; then
    echo "📥 Installation de requests..."
    pip3 install requests --break-system-packages 2>/dev/null || pip3 install requests
fi

# Créer les dossiers nécessaires
mkdir -p logs backups

# Lancer le CLI
python3 cli.py
