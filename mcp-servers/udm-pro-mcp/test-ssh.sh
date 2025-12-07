#!/bin/bash

echo "🧪 Test de connexion SSH au UDM-Pro..."
echo ""

KEY_PATH="$HOME/.ssh/id_rsa_udm"
UDM_HOST="10.10.10.1"
UDM_USER="root"

# Vérifier que la clé existe
if [ ! -f "$KEY_PATH" ]; then
    echo "❌ Clé SSH non trouvée: $KEY_PATH"
    echo ""
    echo "Créez-la avec:"
    echo "  ssh-keygen -t rsa -b 4096 -f $KEY_PATH -N \"\""
    exit 1
fi

echo "✅ Clé SSH trouvée"
echo "   Chemin: $KEY_PATH"
echo "   Permissions: $(stat -c %a $KEY_PATH)"

if [ "$(stat -c %a $KEY_PATH)" != "600" ]; then
    echo "⚠️  Correction des permissions..."
    chmod 600 "$KEY_PATH"
fi

echo ""
echo "📡 Test de connexion..."
echo "   Host: $UDM_HOST"
echo "   User: $UDM_USER"
echo ""

# Test avec timeout
if timeout 5 ssh -i "$KEY_PATH" -o ConnectTimeout=5 -o StrictHostKeyChecking=no "${UDM_USER}@${UDM_HOST}" 'echo "Connection successful!" && hostname && uname -a' 2>/dev/null; then
    echo ""
    echo "✅ Connexion SSH réussie!"
else
    EXIT_CODE=$?
    echo ""
    echo "❌ Connexion SSH échouée (code: $EXIT_CODE)"
    echo ""
    echo "Diagnostics:"
    echo ""
    
    # Test de ping
    echo "1. Test de connectivité réseau..."
    if ping -c 1 -W 2 "$UDM_HOST" &> /dev/null; then
        echo "   ✅ Le host $UDM_HOST est accessible"
    else
        echo "   ❌ Le host $UDM_HOST n'est pas accessible"
        echo "      Vérifiez l'adresse IP et la connexion réseau"
    fi
    
    echo ""
    echo "2. Test du port SSH (22)..."
    if timeout 2 bash -c "echo > /dev/tcp/$UDM_HOST/22" 2>/dev/null; then
        echo "   ✅ Le port SSH est ouvert"
    else
        echo "   ❌ Le port SSH n'est pas accessible"
        echo "      Vérifiez que SSH est activé sur le UDM-Pro"
    fi
    
    echo ""
    echo "3. Vérification de la clé publique..."
    echo "   📋 Clé publique à ajouter sur le UDM-Pro:"
    echo ""
    cat "${KEY_PATH}.pub"
    echo ""
    echo "   Sur le UDM-Pro, ajoutez cette clé dans:"
    echo "   /root/.ssh/authorized_keys"
    
    echo ""
    echo "4. Test verbose (pour plus de détails):"
    echo "   ssh -vvv -i $KEY_PATH ${UDM_USER}@${UDM_HOST}"
    
    exit 1
fi

echo ""
echo "🎉 Le serveur MCP peut maintenant se connecter au UDM-Pro!"
