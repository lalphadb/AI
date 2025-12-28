#!/bin/bash
# 🔑 Configuration des clés API pour Poker Assistant
# Exécute ce script: source setup_keys.sh

echo "🎰 Configuration Poker Assistant"
echo "================================"
echo ""

# GROQ - Gratuit et le plus rapide
read -p "🟢 Clé GROQ (gratuit, rapide) [ENTER pour skip]: " GROQ_KEY
if [ -n "$GROQ_KEY" ]; then
    export GROQ_API_KEY="$GROQ_KEY"
    echo "   ✅ GROQ configuré"
fi

# GOOGLE/GEMINI - Backup rapide
read -p "🔵 Clé GOOGLE/Gemini [ENTER pour skip]: " GOOGLE_KEY
if [ -n "$GOOGLE_KEY" ]; then
    export GOOGLE_API_KEY="$GOOGLE_KEY"
    echo "   ✅ Gemini configuré"
fi

# ANTHROPIC/CLAUDE - Précis
read -p "🟣 Clé ANTHROPIC/Claude [ENTER pour skip]: " ANTHROPIC_KEY
if [ -n "$ANTHROPIC_KEY" ]; then
    export ANTHROPIC_API_KEY="$ANTHROPIC_KEY"
    echo "   ✅ Claude configuré"
fi

echo ""
echo "================================"
echo "✅ Configuration terminée!"
echo ""
echo "🚀 Lance maintenant: python poker_realtime.py"
