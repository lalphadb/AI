"""
MCP-HUB Manager - Gestionnaire centralisé pour tous les MCP
Version: 3.0.0
Date: 2025-09-23

Gestionnaire unifié pour tous les Model Context Protocol servers
"""

import os
import json
import subprocess
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import logging
import yaml

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/studiosdb/MCP-HUB/logs/mcp-hub.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('MCP-HUB')

class MCPServer:
    """Représente un serveur MCP individuel"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.process = None
        self.status = "stopped"
        self.port = config.get('port')
        self.executable = config.get('executable')
        self.args = config.get('args', [])
        self.env = config.get('env', {})
        self.auto_start = config.get('auto_start', False)
        self.health_check_url = config.get('health_check_url')
        self.dependencies = config.get('dependencies', [])
        
    async def start(self) -> bool:
        """Démarrer le serveur MCP"""
        if self.status == "running":
            logger.warning(f"{self.name} est déjà en cours d'exécution")
            return True
            
        try:
            logger.info(f"🚀 Démarrage de {self.name}...")
            
            # Vérifier les dépendances
            for dep in self.dependencies:
                if not self._check_dependency(dep):
                    logger.error(f"❌ Dépendance manquante: {dep}")
                    return False
            
            # Construire la commande
            cmd = [self.executable] + self.args
            
            # Démarrer le processus
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                env={**os.environ, **self.env},
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self.status = "running"
            logger.info(f"✅ {self.name} démarré avec PID {self.process.pid}")
            
            # Vérifier la santé si configuré
            if self.health_check_url:
                await asyncio.sleep(2)  # Attendre que le service démarre
                if await self.health_check():
                    logger.info(f"✅ {self.name} est opérationnel")
                else:
                    logger.warning(f"⚠️ {self.name} démarré mais health check échoué")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur au démarrage de {self.name}: {e}")
            self.status = "error"
            return False
    
    async def stop(self) -> bool:
        """Arrêter le serveur MCP"""
        if self.status != "running" or not self.process:
            logger.warning(f"{self.name} n'est pas en cours d'exécution")
            return True
            
        try:
            logger.info(f"🛑 Arrêt de {self.name}...")
            self.process.terminate()
            
            # Attendre l'arrêt gracieux
            try:
                await asyncio.wait_for(self.process.wait(), timeout=10)
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ Arrêt forcé de {self.name}")
                self.process.kill()
                await self.process.wait()
            
            self.status = "stopped"
            self.process = None
            logger.info(f"✅ {self.name} arrêté")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur à l'arrêt de {self.name}: {e}")
            return False
    
    async def restart(self) -> bool:
        """Redémarrer le serveur MCP"""
        logger.info(f"🔄 Redémarrage de {self.name}...")
        await self.stop()
        await asyncio.sleep(1)
        return await self.start()
    
    async def health_check(self) -> bool:
        """Vérifier l'état de santé du serveur"""
        if not self.health_check_url:
            return self.status == "running"
        
        try:
            # Implémenter le health check HTTP
            # Pour l'instant, on vérifie juste le processus
            return self.process and self.process.returncode is None
        except Exception as e:
            logger.error(f"Health check échoué pour {self.name}: {e}")
            return False
    
    def _check_dependency(self, dep: str) -> bool:
        """Vérifier si une dépendance est installée"""
        result = subprocess.run(
            f"which {dep}",
            shell=True,
            capture_output=True
        )
        return result.returncode == 0
    
    def get_status(self) -> Dict[str, Any]:
        """Obtenir le statut détaillé du serveur"""
        return {
            "name": self.name,
            "status": self.status,
            "pid": self.process.pid if self.process else None,
            "port": self.port,
            "uptime": None,  # À implémenter
            "memory": None,  # À implémenter
            "cpu": None  # À implémenter
        }


class MCPHub:
    """Gestionnaire central pour tous les serveurs MCP"""
    
    def __init__(self, config_path: str = "/home/studiosdb/MCP-HUB/config/hub.json"):
        self.config_path = Path(config_path)
        self.servers: Dict[str, MCPServer] = {}
        self.orchestrator = None
        self.cache_manager = None
        self.monitoring_enabled = False
        
    def load_config(self):
        """Charger la configuration du hub"""
        if not self.config_path.exists():
            logger.warning("Configuration non trouvée, création de la config par défaut")
            self._create_default_config()
        
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        # Charger chaque serveur
        for server_name, server_config in config.get('servers', {}).items():
            if server_config.get('enabled', True):
                self.servers[server_name] = MCPServer(server_name, server_config)
                logger.info(f"✅ Serveur {server_name} chargé")
        
        # Configuration globale
        self.monitoring_enabled = config.get('monitoring', {}).get('enabled', True)
        
        logger.info(f"📋 {len(self.servers)} serveurs MCP chargés")
    
    def _create_default_config(self):
        """Créer une configuration par défaut"""
        default_config = {
            "version": "3.0.0",
            "hub": {
                "name": "MCP-HUB",
                "description": "Centralized MCP Management Hub"
            },
            "servers": {
                "studiosdb": {
                    "enabled": True,
                    "executable": "python3",
                    "args": ["/home/studiosdb/MCP-HUB/servers/studiosdb/main.py"],
                    "port": 8001,
                    "auto_start": True,
                    "health_check_url": "http://localhost:8001/health",
                    "dependencies": ["python3", "mysql"]
                },
                "cloudflare": {
                    "enabled": True,
                    "executable": "node",
                    "args": ["/home/studiosdb/MCP-HUB/servers/cloudflare/index.js"],
                    "port": 8002,
                    "auto_start": False,
                    "dependencies": ["node", "npm"]
                },
                "filesystem": {
                    "enabled": True,
                    "executable": "python3",
                    "args": ["/home/studiosdb/MCP-HUB/servers/filesystem/main.py"],
                    "port": 8003,
                    "auto_start": True,
                    "dependencies": ["python3"]
                },
                "browser": {
                    "enabled": True,
                    "executable": "node",
                    "args": ["/home/studiosdb/MCP-HUB/servers/browser/index.js"],
                    "port": 8004,
                    "auto_start": False,
                    "dependencies": ["node", "npm", "chromium"]
                },
                "ssh-udm": {
                    "enabled": False,
                    "executable": "python3",
                    "args": ["/home/studiosdb/MCP-HUB/servers/ssh-udm/main.py"],
                    "port": 8005,
                    "auto_start": False,
                    "dependencies": ["python3", "ssh"]
                }
            },
            "monitoring": {
                "enabled": True,
                "interval": 60,
                "alerts": {
                    "cpu_threshold": 80,
                    "memory_threshold": 85,
                    "disk_threshold": 90
                }
            },
            "logging": {
                "level": "INFO",
                "file": "/home/studiosdb/MCP-HUB/logs/mcp-hub.log",
                "max_size": "100MB",
                "backup_count": 5
            },
            "cache": {
                "enabled": True,
                "type": "memory",
                "max_size": 1000,
                "ttl": 3600
            }
        }
        
        # Créer le dossier config si nécessaire
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Sauvegarder la configuration
        with open(self.config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        logger.info(f"✅ Configuration par défaut créée: {self.config_path}")
    
    async def start_all(self, auto_only: bool = False):
        """Démarrer tous les serveurs MCP"""
        logger.info("🚀 Démarrage de tous les serveurs MCP...")
        
        results = {}
        for name, server in self.servers.items():
            if auto_only and not server.auto_start:
                continue
            
            success = await server.start()
            results[name] = success
        
        # Résumé
        success_count = sum(1 for r in results.values() if r)
        logger.info(f"✅ {success_count}/{len(results)} serveurs démarrés avec succès")
        
        return results
    
    async def stop_all(self):
        """Arrêter tous les serveurs MCP"""
        logger.info("🛑 Arrêt de tous les serveurs MCP...")
        
        results = {}
        for name, server in self.servers.items():
            success = await server.stop()
            results[name] = success
        
        logger.info("✅ Tous les serveurs arrêtés")
        return results
    
    async def get_status(self) -> Dict[str, Any]:
        """Obtenir le statut de tous les serveurs"""
        status = {
            "hub": {
                "version": "3.0.0",
                "uptime": None,  # À implémenter
                "servers_count": len(self.servers),
                "monitoring": self.monitoring_enabled
            },
            "servers": {}
        }
        
        for name, server in self.servers.items():
            status["servers"][name] = server.get_status()
        
        return status
    
    async def monitor_loop(self):
        """Boucle de monitoring des serveurs"""
        if not self.monitoring_enabled:
            return
        
        logger.info("📊 Démarrage du monitoring...")
        
        while True:
            try:
                # Vérifier l'état de chaque serveur
                for name, server in self.servers.items():
                    if server.status == "running":
                        health = await server.health_check()
                        if not health:
                            logger.warning(f"⚠️ {name} ne répond pas, tentative de redémarrage...")
                            await server.restart()
                
                await asyncio.sleep(60)  # Vérifier toutes les minutes
                
            except Exception as e:
                logger.error(f"Erreur dans le monitoring: {e}")
                await asyncio.sleep(60)


class MCPCLIManager:
    """Interface CLI pour gérer le MCP-HUB"""
    
    def __init__(self):
        self.hub = MCPHub()
        
    async def run_command(self, command: str, args: List[str]):
        """Exécuter une commande CLI"""
        commands = {
            "start": self.cmd_start,
            "stop": self.cmd_stop,
            "restart": self.cmd_restart,
            "status": self.cmd_status,
            "list": self.cmd_list,
            "config": self.cmd_config,
            "logs": self.cmd_logs,
            "help": self.cmd_help
        }
        
        if command in commands:
            return await commands[command](args)
        else:
            print(f"❌ Commande inconnue: {command}")
            return await self.cmd_help([])
    
    async def cmd_start(self, args: List[str]):
        """Démarrer un ou tous les serveurs"""
        self.hub.load_config()
        
        if not args or args[0] == "all":
            results = await self.hub.start_all()
            for name, success in results.items():
                status = "✅" if success else "❌"
                print(f"{status} {name}")
        else:
            server_name = args[0]
            if server_name in self.hub.servers:
                success = await self.hub.servers[server_name].start()
                print(f"{'✅' if success else '❌'} {server_name}")
            else:
                print(f"❌ Serveur inconnu: {server_name}")
    
    async def cmd_stop(self, args: List[str]):
        """Arrêter un ou tous les serveurs"""
        self.hub.load_config()
        
        if not args or args[0] == "all":
            await self.hub.stop_all()
            print("✅ Tous les serveurs arrêtés")
        else:
            server_name = args[0]
            if server_name in self.hub.servers:
                success = await self.hub.servers[server_name].stop()
                print(f"{'✅' if success else '❌'} {server_name} arrêté")
            else:
                print(f"❌ Serveur inconnu: {server_name}")
    
    async def cmd_restart(self, args: List[str]):
        """Redémarrer un serveur"""
        self.hub.load_config()
        
        if not args:
            print("❌ Spécifiez un serveur à redémarrer")
            return
        
        server_name = args[0]
        if server_name in self.hub.servers:
            success = await self.hub.servers[server_name].restart()
            print(f"{'✅' if success else '❌'} {server_name} redémarré")
        else:
            print(f"❌ Serveur inconnu: {server_name}")
    
    async def cmd_status(self, args: List[str]):
        """Afficher le statut"""
        self.hub.load_config()
        status = await self.hub.get_status()
        
        print("\n🎯 MCP-HUB Status")
        print("=" * 50)
        print(f"Version: {status['hub']['version']}")
        print(f"Serveurs: {status['hub']['servers_count']}")
        print(f"Monitoring: {'✅' if status['hub']['monitoring'] else '❌'}")
        print("\n📊 Serveurs:")
        print("-" * 50)
        
        for name, server_status in status['servers'].items():
            status_icon = {
                "running": "🟢",
                "stopped": "🔴",
                "error": "🟠"
            }.get(server_status['status'], "⚪")
            
            print(f"{status_icon} {name:15} {server_status['status']:10}", end="")
            if server_status['port']:
                print(f" Port: {server_status['port']}", end="")
            if server_status['pid']:
                print(f" PID: {server_status['pid']}", end="")
            print()
    
    async def cmd_list(self, args: List[str]):
        """Lister tous les serveurs disponibles"""
        self.hub.load_config()
        
        print("\n📋 Serveurs MCP disponibles:")
        print("-" * 40)
        for name, server in self.hub.servers.items():
            auto = "🚀" if server.auto_start else "  "
            print(f"{auto} {name}")
        print(f"\nTotal: {len(self.hub.servers)} serveurs")
    
    async def cmd_config(self, args: List[str]):
        """Afficher ou éditer la configuration"""
        config_path = "/home/studiosdb/MCP-HUB/config/hub.json"
        
        if not args:
            # Afficher la config
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                print(json.dumps(config, indent=2))
            else:
                print("❌ Configuration non trouvée")
        elif args[0] == "edit":
            # Ouvrir dans l'éditeur
            os.system(f"nano {config_path}")
        elif args[0] == "reload":
            # Recharger la config
            self.hub.load_config()
            print("✅ Configuration rechargée")
    
    async def cmd_logs(self, args: List[str]):
        """Afficher les logs"""
        log_file = "/home/studiosdb/MCP-HUB/logs/mcp-hub.log"
        
        if not args:
            # Afficher les 20 dernières lignes
            os.system(f"tail -n 20 {log_file}")
        elif args[0] == "follow":
            # Suivre les logs en temps réel
            os.system(f"tail -f {log_file}")
        elif args[0].isdigit():
            # Afficher N lignes
            os.system(f"tail -n {args[0]} {log_file}")
    
    async def cmd_help(self, args: List[str]):
        """Afficher l'aide"""
        help_text = """
🎯 MCP-HUB Manager - Commandes disponibles:

  start [server|all]    - Démarrer un serveur ou tous
  stop [server|all]     - Arrêter un serveur ou tous
  restart <server>      - Redémarrer un serveur
  status                - Afficher le statut de tous les serveurs
  list                  - Lister les serveurs disponibles
  config [edit|reload]  - Gérer la configuration
  logs [N|follow]       - Afficher les logs
  help                  - Afficher cette aide

Exemples:
  mcp-hub start all           # Démarrer tous les serveurs
  mcp-hub stop studiosdb      # Arrêter StudiosDB
  mcp-hub restart cloudflare  # Redémarrer Cloudflare
  mcp-hub status              # Voir le statut
  mcp-hub logs follow         # Suivre les logs en temps réel
        """
        print(help_text)


# Point d'entrée principal
async def main():
    import sys
    
    cli = MCPCLIManager()
    
    if len(sys.argv) < 2:
        await cli.cmd_help([])
    else:
        command = sys.argv[1]
        args = sys.argv[2:] if len(sys.argv) > 2 else []
        await cli.run_command(command, args)


if __name__ == "__main__":
    asyncio.run(main())
