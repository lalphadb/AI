#!/bin/bash

# Script de test du serveur MCP Ubuntu
echo "🧪 Test du serveur MCP Ubuntu..."

# Vérifier que le build existe
if [ ! -f "dist/index.js" ]; then
    echo "❌ Le serveur n'est pas compilé. Lancez 'npm run build' d'abord."
    exit 1
fi

# Test 1: Vérifier que le serveur démarre
echo "Test 1: Démarrage du serveur..."
timeout 2 node dist/index.js > /dev/null 2>&1 &
PID=$!
sleep 1

if ps -p $PID > /dev/null; then
    echo "✅ Le serveur démarre correctement"
    kill $PID 2>/dev/null
else
    echo "❌ Le serveur ne démarre pas"
    exit 1
fi

# Test 2: Vérifier les dépendances
echo "Test 2: Vérification des dépendances..."
if npm list @modelcontextprotocol/sdk systeminformation > /dev/null 2>&1; then
    echo "✅ Toutes les dépendances sont installées"
else
    echo "⚠️  Certaines dépendances sont manquantes"
    echo "   Lancez 'npm install' pour les installer"
fi

# Test 3: Vérifier la structure
echo "Test 3: Vérification de la structure..."
REQUIRED_FILES="package.json tsconfig.json src/index.ts README.md"
ALL_OK=true

for file in $REQUIRED_FILES; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file manquant"
        ALL_OK=false
    fi
done

if [ "$ALL_OK" = true ]; then
    echo "✅ Structure du projet correcte"
else
    echo "❌ Structure du projet incomplète"
fi

echo ""
echo "🎉 Tests terminés!"
echo ""
echo "Pour utiliser le serveur:"
echo "1. Configurez Claude Desktop (voir README.md)"
echo "2. Redémarrez Claude Desktop"
echo "3. Utilisez les outils MCP dans vos conversations"
