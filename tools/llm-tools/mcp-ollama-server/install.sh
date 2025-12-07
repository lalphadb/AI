#!/bin/bash
set -e
echo "🦙 Installation du serveur MCP Ollama"
echo "========================================"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "\n${YELLOW}[1/4]${NC} Vérification de Node.js..."
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js n'est pas installé${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Node.js $(node --version) détecté"

echo -e "\n${YELLOW}[2/4]${NC} Installation des dépendances npm..."
npm install

echo -e "\n${YELLOW}[3/4]${NC} Configuration des permissions..."
chmod +x index.js test.sh

echo -e "\n${YELLOW}[4/4]${NC} Vérification d'Ollama..."
if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Ollama est actif"
else
    echo -e "${RED}⚠️  Ollama ne répond pas${NC}"
fi

CLAUDE_CONFIG="$HOME/.config/Claude/claude_desktop_config.json"
CURRENT_DIR=$(pwd)

echo -e "\n${GREEN}✅ Installation terminée!${NC}"
echo ""
echo "Configuration Claude Desktop:"
echo "Ajoutez ceci à $CLAUDE_CONFIG :"
echo ""
cat << EOF
{
  "mcpServers": {
    "ollama": {
      "command": "node",
      "args": ["$CURRENT_DIR/index.js"],
      "env": {
        "OLLAMA_BASE_URL": "http://localhost:11434"
      }
    }
  }
}
EOF
echo ""
echo "Puis redémarrez Claude Desktop!"
