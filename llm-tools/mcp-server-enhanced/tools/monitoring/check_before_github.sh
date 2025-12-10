#!/bin/bash
# 🔍 Vérification avant publication GitHub
# Vérifie que tout est prêt pour être publié

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     🔍 VÉRIFICATION PRÉ-PUBLICATION GITHUB          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

MCP_HUB="/home/studiosdb/MCP-HUB"
ERRORS=0
WARNINGS=0

# Fonction pour afficher les résultats
check_result() {
    if [ $1 -eq 0 ]; then
        echo "✅ $2"
    else
        echo "❌ $2"
        ERRORS=$((ERRORS + 1))
    fi
}

warning() {
    echo "⚠️  $1"
    WARNINGS=$((WARNINGS + 1))
}

# 1. Vérifier que MCP-HUB existe
echo "📁 Vérification de la structure..."
if [ -d "$MCP_HUB" ]; then
    check_result 0 "MCP-HUB existe"
    cd $MCP_HUB
else
    check_result 1 "MCP-HUB n'existe pas"
    echo "   Exécutez: bash /home/studiosdb/install_mcp_hub.sh"
    exit 1
fi

# 2. Vérifier les fichiers essentiels
echo ""
echo "📄 Vérification des fichiers essentiels..."

[ -f "README.md" ] && check_result 0 "README.md" || check_result 1 "README.md manquant"
[ -f "LICENSE" ] && check_result 0 "LICENSE" || check_result 1 "LICENSE manquant"
[ -f ".gitignore" ] && check_result 0 ".gitignore" || check_result 1 ".gitignore manquant"
[ -f "requirements.txt" ] && check_result 0 "requirements.txt" || warning "requirements.txt manquant (optionnel)"
[ -f "mcp-hub.py" ] && check_result 0 "mcp-hub.py" || check_result 1 "mcp-hub.py manquant"

# 3. Vérifier la structure des dossiers
echo ""
echo "📂 Vérification de la structure..."

[ -d "servers" ] && check_result 0 "servers/" || check_result 1 "servers/ manquant"
[ -d "clients" ] && check_result 0 "clients/" || check_result 1 "clients/ manquant"
[ -d "shared" ] && check_result 0 "shared/" || check_result 1 "shared/ manquant"
[ -d "config" ] && check_result 0 "config/" || check_result 1 "config/ manquant"
[ -d "logs" ] && check_result 0 "logs/" || warning "logs/ manquant (sera créé)"

# 4. Vérifier les serveurs MCP
echo ""
echo "🖥️  Vérification des serveurs MCP..."

SERVER_COUNT=$(ls -1 servers/ 2>/dev/null | wc -l)
if [ $SERVER_COUNT -gt 0 ]; then
    check_result 0 "Serveurs MCP trouvés: $SERVER_COUNT"
    echo "   Serveurs disponibles:"
    for server in servers/*/; do
        if [ -d "$server" ]; then
            echo "   - $(basename $server)"
        fi
    done
else
    warning "Aucun serveur MCP trouvé dans servers/"
fi

# 5. Vérifier les fichiers sensibles
echo ""
echo "🔒 Vérification des fichiers sensibles..."

SENSITIVE_FILES=(
    "credentials.json"
    "postfixadmin_credentials.txt"
    "POSTFIXADMIN_LOGIN.txt"
    "config/secrets.json"
    ".env"
    "*.key"
    "*.pem"
)

FOUND_SENSITIVE=0
for pattern in "${SENSITIVE_FILES[@]}"; do
    if ls $pattern 2>/dev/null | grep -q .; then
        warning "Fichier sensible trouvé: $pattern"
        FOUND_SENSITIVE=1
    fi
done

if [ $FOUND_SENSITIVE -eq 0 ]; then
    check_result 0 "Aucun fichier sensible trouvé"
fi

# 6. Vérifier Git
echo ""
echo "🔗 Vérification Git..."

if [ -d ".git" ]; then
    check_result 0 "Repository Git initialisé"
    
    # Vérifier la configuration
    GIT_NAME=$(git config user.name)
    GIT_EMAIL=$(git config user.email)
    
    if [ ! -z "$GIT_NAME" ]; then
        check_result 0 "Git user.name: $GIT_NAME"
    else
        warning "Git user.name non configuré"
    fi
    
    if [ ! -z "$GIT_EMAIL" ]; then
        check_result 0 "Git user.email: $GIT_EMAIL"
    else
        warning "Git user.email non configuré"
    fi
    
    # Vérifier la branche
    BRANCH=$(git branch --show-current)
    if [ "$BRANCH" = "main" ]; then
        check_result 0 "Branche: main"
    else
        warning "Branche actuelle: $BRANCH (devrait être 'main')"
    fi
    
    # Vérifier les remotes
    if git remote | grep -q "origin"; then
        REMOTE_URL=$(git remote get-url origin)
        check_result 0 "Remote origin: $REMOTE_URL"
    else
        warning "Remote 'origin' non configuré"
    fi
    
    # Vérifier s'il y a des changements non commités
    if git status --porcelain | grep -q .; then
        warning "Changements non commités détectés"
        echo "   Utilisez: git status"
    else
        check_result 0 "Pas de changements non commités"
    fi
    
else
    check_result 1 "Repository Git non initialisé"
    echo "   Exécutez: git init"
fi

# 7. Vérifier la taille du projet
echo ""
echo "💾 Vérification de la taille..."

TOTAL_SIZE=$(du -sh . | cut -f1)
echo "   Taille totale: $TOTAL_SIZE"

# Vérifier les gros fichiers
echo "   Fichiers > 50MB:"
find . -type f -size +50M 2>/dev/null | while read file; do
    SIZE=$(du -h "$file" | cut -f1)
    warning "Gros fichier: $file ($SIZE)"
done

# 8. Vérifier les dépendances Python
echo ""
echo "🐍 Vérification Python..."

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    check_result 0 "$PYTHON_VERSION"
else
    check_result 1 "Python3 non installé"
fi

# 9. Résumé
echo ""
echo "══════════════════════════════════════════════════════"
echo "                    📊 RÉSUMÉ                         "
echo "══════════════════════════════════════════════════════"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo "🎉 PARFAIT ! Tout est prêt pour GitHub !"
    echo ""
    echo "Prochaines étapes:"
    echo "1. cd $MCP_HUB"
    echo "2. git add ."
    echo "3. git commit -m 'Initial commit: MCP-HUB v3.0.0'"
    echo "4. git push -u origin main"
elif [ $ERRORS -eq 0 ]; then
    echo "✅ Prêt avec $WARNINGS avertissement(s)"
    echo ""
    echo "Les avertissements ne sont pas bloquants."
    echo "Vous pouvez continuer la publication."
else
    echo "❌ $ERRORS erreur(s) et $WARNINGS avertissement(s)"
    echo ""
    echo "Corrigez les erreurs avant de publier."
fi

echo ""
echo "══════════════════════════════════════════════════════"
echo ""

# Proposer des actions
if [ $ERRORS -gt 0 ]; then
    echo "🔧 Actions correctives suggérées:"
    echo ""
    echo "1. Si MCP-HUB n'est pas installé:"
    echo "   bash /home/studiosdb/install_mcp_hub.sh"
    echo ""
    echo "2. Si des fichiers manquent:"
    echo "   bash /home/studiosdb/publish_mcp_hub_github.sh"
    echo ""
elif [ $WARNINGS -gt 0 ]; then
    echo "💡 Suggestions:"
    echo ""
    if [ $FOUND_SENSITIVE -eq 1 ]; then
        echo "- Vérifiez que .gitignore exclut les fichiers sensibles"
        echo "- Supprimez ou déplacez les fichiers credentials"
    fi
    echo ""
fi

exit $ERRORS
