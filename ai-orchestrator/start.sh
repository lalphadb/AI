#!/bin/bash
cd /home/lalpha/projets/ai-tools/ai-orchestrator/backend

export OLLAMA_URL=http://127.0.0.1:11434

# Lancer le backend
exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8001
