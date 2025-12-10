#!/bin/bash
cd "$(dirname "$0")"
echo "🚀 Démarrage API Agent 4LB..."
pip install fastapi uvicorn requests --quiet 2>/dev/null
mkdir -p memory logs
export OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5-coder:32b}"
export API_PORT="${API_PORT:-8889}"
echo "📡 API: http://0.0.0.0:$API_PORT"
echo "🤖 Ollama: $OLLAMA_HOST ($OLLAMA_MODEL)"
python3 -m uvicorn api.server:app --host 0.0.0.0 --port $API_PORT --reload
