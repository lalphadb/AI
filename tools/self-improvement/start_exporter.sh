#!/bin/bash
cd /home/lalpha/projets/ai-tools/self-improvement
pkill -f "metrics_exporter.py" 2>/dev/null || true
sleep 1
nohup python3 metrics_exporter.py > exporter.log 2>&1 &
echo "✅ Exporter démarré (PID: $!)"
sleep 2
curl -s http://localhost:9101/health && echo " - Health OK"
