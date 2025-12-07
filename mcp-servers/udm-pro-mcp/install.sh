#!/bin/bash

echo "🚀 Installation du serveur MCP UDM-Pro..."

# Vérifier Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js n'est pas installé."
    exit 1
fi

echo "✅ Node.js $(node -v) détecté"

# Installation des dépendances
echo "📦 Installation des dépendances..."
npm install

# Build
echo "🔨 Compilation TypeScript..."
npm run build

# Vérifier que la clé SSH existe
KEY_PATH="$HOME/.ssh/id_rsa_udm"

if [ ! -f "$KEY_PATH" ]; then
    echo ""
    echo "⚠️  Clé SSH non trouvée à $KEY_PATH"
    echo ""
    echo "Options:"
    echo "  1) Créer une nouvelle clé:"
    echo "     ssh-keygen -t rsa -b 4096 -f $KEY_PATH -N \"\""
    echo ""
    echo "  2) Copier une clé existante:"
    echo "     cp /chemin/vers/votre/cle $KEY_PATH"
    echo "     chmod 600 $KEY_PATH"
    echo ""
    read -p "Voulez-vous créer une nouvelle clé maintenant? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ssh-keygen -t rsa -b 4096 -f "$KEY_PATH" -N ""
        echo ""
        echo "✅ Clé créée!"
        echo ""
        echo "📋 Copiez cette clé publique sur votre UDM-Pro:"
        cat "${KEY_PATH}.pub"
        echo ""
        echo "Sur le UDM-Pro, ajoutez-la dans /root/.ssh/authorized_keys"
    fi
else
    echo "✅ Clé SSH trouvée: $KEY_PATH"
    chmod 600 "$KEY_PATH"
fi

# Test de connexion SSH
echo ""
echo "🧪 Test de connexion SSH..."
if ssh -i "$KEY_PATH" -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@10.10.10.1 'hostname' &> /dev/null; then
    echo "✅ Connexion SSH réussie!"
else
    echo "⚠️  Connexion SSH échouée"
    echo "    Vérifiez que:"
    echo "    - Le UDM-Pro est accessible sur 10.10.10.1"
    echo "    - La clé publique est ajoutée sur le UDM-Pro"
    echo "    - Le service SSH est actif sur le UDM-Pro"
fi

# Configuration Claude Desktop
CONFIG_FILE="$HOME/.config/Claude/claude_desktop_config.json"
CONFIG_DIR="$HOME/.config/Claude"

echo ""
echo "📝 Configuration Claude Desktop..."

if [ ! -d "$CONFIG_DIR" ]; then
    mkdir -p "$CONFIG_DIR"
fi

if [ -f "$CONFIG_FILE" ]; then
    echo "⚠️  Un fichier de configuration existe déjà"
    echo "    Sauvegarde: ${CONFIG_FILE}.backup"
    cp "$CONFIG_FILE" "${CONFIG_FILE}.backup"
fi

cat > "$CONFIG_FILE" << EOF
{
  "mcpServers": {
    "udm-pro": {
      "command": "node",
      "args": ["$(pwd)/dist/index.js"]
    }
  }
}
EOF

echo "✅ Configuration créée!"

echo ""
echo "🎉 Installation terminée!"
echo ""
echo "📋 Prochaines étapes:"
echo "  1. Assurez-vous que la clé SSH est configurée sur le UDM-Pro"
echo "  2. Fermez complètement Claude Desktop"
echo "  3. Relancez Claude Desktop"
echo "  4. Testez avec: 'Teste la connexion à mon UDM-Pro'"
echo ""
