#!/bin/bash
cd /home/lalpha/projets/developpement/mcp-filesystem-server
npm install
echo "Installation terminée. Configuration pour Open WebUI:"
echo ""
echo "1. Dans Open WebUI, ajoutez cette configuration MCP:"
echo "   URL: stdio:/home/lalpha/projets/developpement/mcp-filesystem-server/index.js"
echo ""
echo "2. Les outils disponibles:"
echo "   - analyze_directory: Trouve fichiers inutilisés/anciens/volumineux"
echo "   - find_duplicates: Détecte les doublons"
echo "   - check_dependencies: Vérifie dépendances npm non utilisées"
echo "   - disk_usage: Analyse utilisation disque par dossier"
echo ""
echo "3. Exemple d'utilisation dans Open WebUI:"
echo '   "Analyse /home/project et dis-moi ce qui nest pas utilisé"'
