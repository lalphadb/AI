#!/bin/bash

echo "🧹 Script de nettoyage des disques - StudiosDB"
echo "============================================="
echo ""

# Calculer l'espace avant nettoyage
BEFORE=$(df -h / | awk 'NR==2 {print $4}')
echo "📊 Espace disponible avant : $BEFORE"
echo ""

# 1. Nettoyer le cache VS Code
echo "1️⃣ Nettoyage du cache VS Code..."
rm -rf /home/studiosdb/.config/Code/Cache/* 2>/dev/null
rm -rf /home/studiosdb/.config/Code/CachedData/* 2>/dev/null
rm -rf /home/studiosdb/.config/Code/CachedExtensionVSIXs/* 2>/dev/null
rm -rf /home/studiosdb/.config/Code/User/workspaceStorage/*/chatSessions/*.json 2>/dev/null
echo "   ✅ Cache VS Code nettoyé"

# 2. Nettoyer le cache Vivaldi
echo "2️⃣ Nettoyage du cache Vivaldi..."
rm -rf /home/studiosdb/.config/vivaldi/Default/Cache/* 2>/dev/null
rm -rf /home/studiosdb/.config/vivaldi/Default/Code\ Cache/* 2>/dev/null
rm -rf /home/studiosdb/.config/vivaldi/component_crx_cache/* 2>/dev/null
echo "   ✅ Cache Vivaldi nettoyé"

# 3. Nettoyer les node_modules inutiles
echo "3️⃣ Nettoyage des node_modules des sauvegardes..."
rm -rf /home/studiosdb/Desktop/web/sauvegardes/*/node_modules 2>/dev/null
rm -rf /home/studiosdb/studiosunisdb/node_modules 2>/dev/null
rm -rf /home/studiosdb/.local/share/Trash/expunged/*/node_modules 2>/dev/null
echo "   ✅ Node_modules des sauvegardes supprimés"

# 4. Vider la corbeille
echo "4️⃣ Vidage de la corbeille..."
rm -rf /home/studiosdb/.local/share/Trash/files/* 2>/dev/null
rm -rf /home/studiosdb/.local/share/Trash/info/* 2>/dev/null
rm -rf /home/studiosdb/.local/share/Trash/expunged/* 2>/dev/null
echo "   ✅ Corbeille vidée"

# 5. Nettoyer les anciennes extensions VS Code
echo "5️⃣ Nettoyage des anciennes extensions VS Code..."
# Garder seulement les dernières versions
rm -rf /home/studiosdb/.vscode/extensions/github.copilot-chat-0.31.1 2>/dev/null
rm -rf /home/studiosdb/.vscode/extensions/github.copilot-chat-0.31.2 2>/dev/null
rm -rf /home/studiosdb/.vscode/extensions/ms-azuretools.vscode-containers-2.1.0 2>/dev/null
echo "   ✅ Anciennes extensions supprimées"

# 6. Nettoyer les fichiers temporaires
echo "6️⃣ Nettoyage des fichiers temporaires..."
rm -rf /tmp/* 2>/dev/null
rm -rf /home/studiosdb/.cache/* 2>/dev/null
echo "   ✅ Fichiers temporaires nettoyés"

# 7. Nettoyer les gros fichiers logs dans .config/Code
echo "7️⃣ Nettoyage des gros fichiers de workspace..."
find /home/studiosdb/.config/Code/User/workspaceStorage -type f -size +50M -delete 2>/dev/null
echo "   ✅ Gros fichiers de workspace supprimés"

# 8. Nettoyer npm cache (déjà fait mais au cas où)
echo "8️⃣ Nettoyage final du cache NPM..."
npm cache clean --force 2>/dev/null
echo "   ✅ Cache NPM nettoyé"

echo ""
echo "============================================="
# Calculer l'espace après nettoyage
AFTER=$(df -h / | awk 'NR==2 {print $4}')
echo "📊 Espace disponible après : $AFTER"
echo "✨ Nettoyage terminé avec succès !"
