#!/bin/bash

# Configuration des chemins
MCP_DIR="$HOME/projets/ai-tools/mcp-servers/custom-admin-mcp"
VENV_DIR="$MCP_DIR/venv"
LOG_DIR="/var/log/mcp"

echo "🚀 Début de l'installation du serveur MCP 4LB..."

# 1. Création du dossier
mkdir -p $MCP_DIR
cd $MCP_DIR

# 2. Création de l'environnement virtuel et installation
python3 -m venv venv
source venv/bin/activate
pip install mcp flask fastmcp

# 3. Création du fichier server.py
cat <<EOF > server.py
from mcp.server.fastmcp import FastMCP
import subprocess
import os

mcp = FastMCP("4LB-Admin-Server")

@mcp.tool()
def get_gpu_status() -> str:
    """Récupère l'état détaillé de la RTX 5070 Ti."""
    try:
        result = subprocess.check_output(["nvidia-smi", "--query-gpu=utilization.gpu,memory.total,memory.used,temp.gpu", "--format=csv,noheader,nounits"])
        return f"Utilisation GPU: {result.decode().strip()}"
    except Exception as e:
        return f"Erreur GPU: {str(e)}"

@mcp.tool()
def clean_docker_logs(container_name: str) -> str:
    """Nettoie les logs d'un container spécifique."""
    try:
        cmd = f"docker inspect --format='{{{{.LogPath}}}}' {container_name} | xargs truncate -s 0"
        subprocess.run(cmd, shell=True, check=True)
        return f"✅ Logs de {container_name} vidés."
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

if __name__ == "__main__":
    mcp.run()
EOF

# 4. Création du service Systemd (nécessite sudo)
echo "⚙️ Configuration du service Systemd..."
sudo cat <<EOF | sudo tee /etc/systemd/system/mcp-4lb.service
[Unit]
Description=MCP Server for 4LB.ca
After=network.target docker.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$MCP_DIR
ExecStart=$VENV_DIR/bin/python $MCP_DIR/server.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 5. Activation
sudo systemctl daemon-reload
sudo systemctl enable mcp-4lb.service
sudo systemctl start mcp-4lb.service

echo "✅ Installation terminée ! Le serveur MCP est actif."
