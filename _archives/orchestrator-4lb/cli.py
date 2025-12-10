#!/usr/bin/env python3
"""
🖥️ CLI Interactif - Orchestrateur 4LB

Usage:
    ./cli.py
    python3 cli.py
"""

import os
import sys
import json
import readline
from pathlib import Path
from typing import Optional, Dict, Any

# Ajouter le répertoire courant au path
sys.path.insert(0, str(Path(__file__).parent))

from modules import (
    base_tools, gitops_tools, backup_tools, self_improve_tools,
    TOOLS_CATALOG, get_tool_count
)

# Couleurs ANSI
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


class OrchestratorCLI:
    """CLI interactif pour l'Orchestrateur 4LB"""
    
    def __init__(self):
        self.running = True
        self.history = []
        
        # Mapper tous les outils
        self.tools = {
            # Base
            "read_file": base_tools.read_file,
            "write_file": base_tools.write_file,
            "propose_diff": base_tools.propose_diff,
            "apply_diff": base_tools.apply_diff,
            "run_command": base_tools.run_command,
            "list_directory": base_tools.list_directory,
            "file_exists": base_tools.file_exists,
            "get_system_info": base_tools.get_system_info,
            "docker_status": base_tools.docker_status,
            "list_pending_diffs": base_tools.list_pending_diffs,
            
            # GitOps
            "gitops_init": gitops_tools.gitops_init,
            "gitops_status": gitops_tools.gitops_status,
            "gitops_commit": gitops_tools.gitops_commit,
            "gitops_rollback": gitops_tools.gitops_rollback,
            "gitops_setup_hooks": gitops_tools.gitops_setup_hooks,
            "gitops_log": gitops_tools.gitops_log,
            
            # Backup
            "backup_postgres": backup_tools.backup_postgres,
            "backup_configs": backup_tools.backup_configs,
            "backup_ollama_models": backup_tools.backup_ollama_models,
            "backup_full": backup_tools.backup_full,
            "backup_s3": backup_tools.backup_s3,
            "list_backups": backup_tools.list_backups,
            "cleanup_old_backups": backup_tools.cleanup_old_backups,
            
            # Self-Improve
            "self_improve_analyze_logs": self_improve_tools.self_improve_analyze_logs,
            "self_improve_anomalies": self_improve_tools.self_improve_anomalies,
            "self_improve_suggestions": self_improve_tools.self_improve_suggestions,
            "test_ollama": self_improve_tools.test_ollama_connection,
        }
        
        # Commandes spéciales
        self.commands = {
            "help": self.show_help,
            "?": self.show_help,
            "tools": self.list_tools,
            "exit": self.exit_cli,
            "quit": self.exit_cli,
            "q": self.exit_cli,
            "clear": self.clear_screen,
            "history": self.show_history,
            "status": self.show_status,
        }
    
    def print_banner(self):
        """Afficher la bannière"""
        banner = f"""
{Colors.CYAN}{Colors.BOLD}
  ╔═══════════════════════════════════════════════════════════╗
  ║           🎛️  ORCHESTRATEUR 4LB v1.0                      ║
  ║        Infrastructure IA Self-Improving                   ║
  ╚═══════════════════════════════════════════════════════════╝
{Colors.END}
  {Colors.GREEN}✓ {get_tool_count()} outils disponibles{Colors.END}
  {Colors.BLUE}Tapez 'help' pour voir les commandes disponibles{Colors.END}
  {Colors.YELLOW}Tapez 'tools' pour voir la liste des outils{Colors.END}
"""
        print(banner)
    
    def show_help(self, *args):
        """Afficher l'aide"""
        help_text = f"""
{Colors.BOLD}Commandes:{Colors.END}
  help, ?       Afficher cette aide
  tools         Lister tous les outils disponibles
  status        Afficher le statut du système
  history       Afficher l'historique des commandes
  clear         Effacer l'écran
  exit, quit, q Quitter

{Colors.BOLD}Utilisation des outils:{Colors.END}
  <nom_outil>                    Exécuter sans paramètres
  <nom_outil> param1=val1        Exécuter avec paramètres

{Colors.BOLD}Exemples:{Colors.END}
  docker_status
  read_file path=/etc/hostname
  gitops_status
  backup_full
  self_improve_anomalies
  run_command command="df -h"
"""
        print(help_text)
        return {"success": True}
    
    def list_tools(self, *args):
        """Lister les outils disponibles"""
        print(f"\n{Colors.BOLD}📦 Outils disponibles ({get_tool_count()} total):{Colors.END}\n")
        
        for module_name, module_info in TOOLS_CATALOG.items():
            print(f"{Colors.CYAN}{Colors.BOLD}[{module_name}]{Colors.END} - {module_info['description']}")
            for tool in module_info['tools']:
                print(f"  • {tool}")
            print()
        
        return {"success": True}
    
    def show_status(self, *args):
        """Afficher le statut du système"""
        print(f"\n{Colors.BOLD}📊 Statut Système:{Colors.END}\n")
        
        # Test Ollama
        print(f"{Colors.CYAN}Ollama:{Colors.END} ", end="")
        ollama_result = self.tools["test_ollama"]()
        if ollama_result.get("success"):
            print(f"{Colors.GREEN}✓ Connecté{Colors.END}")
            print(f"  Modèles: {', '.join(ollama_result.get('models', []))}")
        else:
            print(f"{Colors.RED}✗ Non disponible{Colors.END}")
        
        # Docker
        print(f"\n{Colors.CYAN}Docker:{Colors.END} ", end="")
        docker_result = self.tools["docker_status"]()
        if docker_result.get("success"):
            print(f"{Colors.GREEN}✓ {docker_result.get('running', 0)} conteneurs actifs{Colors.END}")
        else:
            print(f"{Colors.RED}✗ Erreur{Colors.END}")
        
        # Système
        print(f"\n{Colors.CYAN}Système:{Colors.END}")
        system_result = self.tools["get_system_info"]()
        if system_result.get("success"):
            info = system_result.get("info", {})
            if "hostname" in info:
                print(f"  Hostname: {info['hostname']}")
            if "cpu_cores" in info:
                print(f"  CPU: {info['cpu_cores']} cores")
            if "gpu" in info:
                print(f"  GPU: {info['gpu']}")
        
        print()
        return {"success": True}
    
    def show_history(self, *args):
        """Afficher l'historique"""
        print(f"\n{Colors.BOLD}📜 Historique des commandes:{Colors.END}\n")
        for i, cmd in enumerate(self.history[-20:], 1):
            print(f"  {i}. {cmd}")
        print()
        return {"success": True}
    
    def clear_screen(self, *args):
        """Effacer l'écran"""
        os.system('clear' if os.name == 'posix' else 'cls')
        self.print_banner()
        return {"success": True}
    
    def exit_cli(self, *args):
        """Quitter le CLI"""
        self.running = False
        print(f"\n{Colors.YELLOW}👋 Au revoir!{Colors.END}\n")
        return {"success": True}
    
    def parse_params(self, args_str: str) -> Dict[str, Any]:
        """Parser les paramètres de la forme key=value"""
        params = {}
        
        if not args_str.strip():
            return params
        
        # Gérer les guillemets pour les valeurs avec espaces
        import shlex
        try:
            parts = shlex.split(args_str)
        except ValueError:
            parts = args_str.split()
        
        for part in parts:
            if "=" in part:
                key, value = part.split("=", 1)
                
                # Convertir les types
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value.isdigit():
                    value = int(value)
                
                params[key.strip()] = value
        
        return params
    
    def execute(self, input_str: str):
        """Exécuter une commande ou un outil"""
        input_str = input_str.strip()
        
        if not input_str:
            return
        
        # Ajouter à l'historique
        self.history.append(input_str)
        
        # Parser la commande
        parts = input_str.split(maxsplit=1)
        cmd = parts[0].lower()
        args_str = parts[1] if len(parts) > 1 else ""
        
        # Vérifier si c'est une commande spéciale
        if cmd in self.commands:
            return self.commands[cmd](args_str)
        
        # Vérifier si c'est un outil
        if cmd in self.tools:
            params = self.parse_params(args_str)
            
            print(f"\n{Colors.CYAN}⏳ Exécution de {cmd}...{Colors.END}\n")
            
            try:
                result = self.tools[cmd](**params)
                
                # Afficher le résultat
                if result.get("success"):
                    print(f"{Colors.GREEN}✓ Succès{Colors.END}\n")
                else:
                    print(f"{Colors.RED}✗ Échec{Colors.END}\n")
                
                # Afficher le JSON formaté
                print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
                print()
                
                return result
                
            except Exception as e:
                print(f"{Colors.RED}❌ Erreur: {e}{Colors.END}\n")
                return {"success": False, "error": str(e)}
        
        # Commande inconnue
        print(f"{Colors.RED}❓ Commande inconnue: {cmd}{Colors.END}")
        print(f"Tapez 'help' pour l'aide ou 'tools' pour la liste des outils.\n")
        return {"success": False, "error": "Commande inconnue"}
    
    def run(self):
        """Boucle principale du CLI"""
        self.print_banner()
        
        # Configuration readline pour l'autocomplétion
        readline.parse_and_bind("tab: complete")
        
        all_completions = list(self.commands.keys()) + list(self.tools.keys())
        
        def completer(text, state):
            options = [c for c in all_completions if c.startswith(text)]
            if state < len(options):
                return options[state]
            return None
        
        readline.set_completer(completer)
        
        while self.running:
            try:
                prompt = f"{Colors.BOLD}{Colors.BLUE}orchestrator>{Colors.END} "
                user_input = input(prompt)
                self.execute(user_input)
                
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}Ctrl+C détecté. Tapez 'exit' pour quitter.{Colors.END}")
            except EOFError:
                self.exit_cli()


def main():
    """Point d'entrée"""
    cli = OrchestratorCLI()
    cli.run()


if __name__ == "__main__":
    main()
