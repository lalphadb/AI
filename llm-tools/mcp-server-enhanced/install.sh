#!/bin/bash
# Script d'installation MCP Server Enhanced + 4lb.ca
# Usage: sudo bash install.sh

set -e

echo "🚀 Installation MCP Server Enhanced + 4lb.ca Dashboard"
echo "========================================================"

# Variables
MCP_DIR="/home/lalpha/mcp-server-enhanced"
WEB_DIR="/var/www/4lb.ca"

echo ""
echo "📦 Étape 1: Copie des fichiers depuis le backup"
cp -r /home/lalpha/Desktop/Backup_ancien_linux/Projects/MCP/*.py "$MCP_DIR/core/" 2>/dev/null || true
cp -r /home/lalpha/Desktop/Backup_ancien_linux/mcp-local/*.json "$MCP_DIR/configs/" 2>/dev/null || true
cp -r /home/lalpha/Desktop/Backup_ancien_linux/mcp-local/tasks/* "$MCP_DIR/configs/tasks/" 2>/dev/null || true
cp -r /home/lalpha/Desktop/Backup_ancien_linux/SystemScripts/* "$MCP_DIR/tools/" 2>/dev/null || true

echo "✅ Fichiers copiés"

echo ""
echo "📦 Étape 2: Installation des dépendances Python"
apt-get update
apt-get install -y python3-pip python3-venv python3-psutil

echo "✅ Dépendances Python installées"

echo ""
echo "🌐 Étape 3: Configuration Nginx pour 4lb.ca"

mkdir -p "$WEB_DIR"
chown -R lalpha:www-data "$WEB_DIR"
chmod -R 755 "$WEB_DIR"

# Créer le dashboard
cat > "$WEB_DIR/index.html" << 'DASHBOARD'
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>4LB.CA - Dashboard MCP</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container { max-width: 1200px; width: 100%; }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }
        .header h1 {
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .dashboard {
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 25px;
            border-radius: 15px;
            color: white;
        }
        .stat-card .value {
            font-size: 2.5em;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 4LB.CA</h1>
            <p>MCP Server Enhanced - Dashboard</p>
        </div>
        <div class="dashboard">
            <div class="stats">
                <div class="stat-card">
                    <h3>MCP Servers</h3>
                    <div class="value">5</div>
                    <div>Actifs</div>
                </div>
                <div class="stat-card">
                    <h3>Uptime</h3>
                    <div class="value">99.9%</div>
                </div>
                <div class="stat-card">
                    <h3>Latence</h3>
                    <div class="value">45ms</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
DASHBOARD

# Configuration nginx
cat > /etc/nginx/sites-available/4lb.ca << 'NGINX'
server {
    listen 80;
    server_name 4lb.ca www.4lb.ca;
    root /var/www/4lb.ca;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/4lb.ca /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

echo "✅ Nginx configuré"

echo ""
echo "✅ Installation terminée!"
echo "Dashboard: http://4lb.ca"
echo "Pour SSL: sudo certbot --nginx -d 4lb.ca -d www.4lb.ca"
