#!/bin/bash
# Démarrer mcpo proxy pour Open WebUI
cd /home/lalpha/projets/ai-tools/mcp-servers

export PATH="/home/lalpha/.local/bin:$PATH"

# Lancer mcpo sur le port 8001
mcpo --port 8001 --api-key "lalpha-mcp-secret" --config ./mcpo-config.json &

echo "mcpo démarré sur http://localhost:8001"
echo "Documentation: http://localhost:8001/docs"
