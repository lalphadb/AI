#!/bin/bash

# Script d'installation du serveur MCP Ubuntu
echo "🚀 Installation du serveur MCP Ubuntu..."

# Vérifier Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js n'est pas installé. Veuillez l'installer d'abord."
    echo "   sudo apt update && sudo apt install -y nodejs npm"
    exit 1
fi

# Vérifier la version de Node.js
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "⚠️  Node.js version 18+ requis. Version actuelle: $(node -v)"
    exit 1
fi

echo "✅ Node.js $(node -v) détecté"

# Installation des dépendances
echo "📦 Installation des dépendances npm..."
npm install

# Build du projet
echo "🔨 Compilation TypeScript..."
npm run build

# Création du dossier de backups
echo "📁 Création du dossier de backups..."
mkdir -p ~/backups

# Chemin du fichier de config Claude Desktop
CONFIG_DIR="$HOME/.config/Claude"
CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"

echo ""
echo "✅ Installation terminée!"
echo ""
echo "📋 Configuration Claude Desktop:"
echo "   Fichier: $CONFIG_FILE"
echo ""
echo "   Ajoutez cette configuration:"
echo ""
echo '   {'
echo '     "mcpServers": {'
echo '       "ubuntu-server": {'
echo '         "command": "node",'
echo "         \"args\": [\"$(pwd)/dist/index.js\"]"
echo '       }'
echo '     }'
echo '   }'
echo ""
echo "⚠️  Note: Si vous avez déjà d'autres serveurs MCP configurés,"
echo "   fusionnez cette configuration avec l'existante."
echo ""
echo "🔄 N'oubliez pas de redémarrer Claude Desktop après la configuration!"
echo ""

# Proposer de créer automatiquement la config
read -p "Voulez-vous que je configure automatiquement Claude Desktop? (o/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Oo]$ ]]; then
    mkdir -p "$CONFIG_DIR"
    
    if [ -f "$CONFIG_FILE" ]; then
        echo "⚠️  Un fichier de configuration existe déjà."
        echo "   Sauvegarde créée: ${CONFIG_FILE}.backup"
        cp "$CONFIG_FILE" "${CONFIG_FILE}.backup"
    fi
    
    cat > "$CONFIG_FILE" << EOF
{
  "mcpServers": {
    "ubuntu-server": {
      "command": "node",
      "args": ["$(pwd)/dist/index.js"]
    }
  }
}
EOF
    echo "✅ Configuration créée avec succès!"
    echo "🔄 Veuillez redémarrer Claude Desktop"
fi

echo ""
echo "🎉 Le serveur MCP Ubuntu est prêt à l'emploi!"
echo "   Consultez le README.md pour plus d'informations."
