#!/usr/bin/env python3
"""
🎮 CLI Interactif pour Agent 4LB
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import readline
from core.config import AGENT_NAME, OLLAMA_MODEL, DEFAULT_LLM
from core.agent import Agent4LB

COLORS = {"reset": "\033[0m", "cyan": "\033[96m", "green": "\033[92m", "yellow": "\033[93m",
          "red": "\033[91m", "blue": "\033[94m", "magenta": "\033[95m", "bold": "\033[1m"}

class AgentCLI:
    def __init__(self):
        self.agent = Agent4LB()
        self.mode = "task"
        self.verbose = True
        self.running = True
    
    def print_color(self, text: str, color: str = "reset"):
        print(f"{COLORS.get(color, '')}{text}{COLORS['reset']}")
    
    def print_banner(self):
        banner = f"""
{COLORS['cyan']}{COLORS['bold']}
    ╔═══════════════════════════════════════════════════════╗
    ║           🧠 {AGENT_NAME} - CLI v1.0                  ║
    ║         Agent IA Autonome pour Infrastructure         ║
    ╚═══════════════════════════════════════════════════════╝
{COLORS['reset']}
    LLM: {COLORS['green']}{self.agent.llm}{COLORS['reset']} ({OLLAMA_MODEL})
    Mode: {COLORS['yellow']}{self.mode.upper()}{COLORS['reset']}
    
    Commandes: {COLORS['blue']}help, mode, verbose, llm, status, history, exit{COLORS['reset']}
"""
        print(banner)
    
    def cmd_help(self):
        help_text = f"""
{COLORS['bold']}Commandes disponibles:{COLORS['reset']}
  {COLORS['cyan']}help{COLORS['reset']}     - Afficher cette aide
  {COLORS['cyan']}mode{COLORS['reset']}     - Basculer entre TASK et CHAT
  {COLORS['cyan']}verbose{COLORS['reset']}  - Activer/désactiver mode verbeux
  {COLORS['cyan']}llm{COLORS['reset']}      - Changer de LLM (ollama/claude)
  {COLORS['cyan']}status{COLORS['reset']}   - Afficher statut système
  {COLORS['cyan']}history{COLORS['reset']}  - Voir historique des tâches
  {COLORS['cyan']}memory{COLORS['reset']}   - Stats mémoire
  {COLORS['cyan']}clear{COLORS['reset']}    - Effacer l'écran
  {COLORS['cyan']}reset{COLORS['reset']}    - Réinitialiser l'agent
  {COLORS['cyan']}exit{COLORS['reset']}     - Quitter

{COLORS['bold']}Modes:{COLORS['reset']}
  {COLORS['yellow']}TASK{COLORS['reset']} - Exécution autonome (réflexion + actions)
  {COLORS['yellow']}CHAT{COLORS['reset']} - Conversation simple
"""
        print(help_text)
    
    def cmd_mode(self):
        self.mode = "chat" if self.mode == "task" else "task"
        self.print_color(f"Mode: {self.mode.upper()}", "green")
    
    def cmd_verbose(self):
        self.verbose = not self.verbose
        self.print_color(f"Verbose: {'ON' if self.verbose else 'OFF'}", "green")
    
    def cmd_llm(self):
        self.agent.llm = "claude" if self.agent.llm == "ollama" else "ollama"
        self.print_color(f"LLM: {self.agent.llm}", "green")
    
    def cmd_status(self):
        from tools.system_tools import system_info
        self.print_color("\n📊 Statut Système:", "bold")
        print(system_info())
    
    def cmd_history(self):
        from memory.persistent import memory
        tasks = memory.get_task_history(10)
        self.print_color("\n📜 Historique des tâches:", "bold")
        for t in tasks:
            status_color = "green" if t["status"] == "completed" else "red"
            self.print_color(f"  [{t['status']}] {t['task'][:50]}... ({t['iterations']} iter)", status_color)
    
    def cmd_memory(self):
        from memory.persistent import memory
        stats = memory.get_stats()
        self.print_color(f"\n💾 Mémoire: {stats}", "cyan")
    
    def process_input(self, user_input: str):
        cmd = user_input.strip().lower()
        if cmd == "help": self.cmd_help()
        elif cmd == "mode": self.cmd_mode()
        elif cmd == "verbose": self.cmd_verbose()
        elif cmd == "llm": self.cmd_llm()
        elif cmd == "status": self.cmd_status()
        elif cmd == "history": self.cmd_history()
        elif cmd == "memory": self.cmd_memory()
        elif cmd == "clear": print("\033[2J\033[H")
        elif cmd == "reset": self.agent.reset(); self.print_color("Agent réinitialisé", "green")
        elif cmd in ["exit", "quit", "q"]: self.running = False
        elif user_input.strip():
            if self.mode == "task":
                result = self.agent.run(user_input, verbose=self.verbose)
                if not self.verbose: self.print_color(f"\n✅ Résultat:\n{result}", "green")
            else:
                response = self.agent.chat(user_input)
                self.print_color(f"\n🤖 {response}", "cyan")
    
    def run(self):
        self.print_banner()
        while self.running:
            try:
                prompt = f"{COLORS['yellow']}[{self.mode.upper()}]{COLORS['reset']} > "
                user_input = input(prompt)
                self.process_input(user_input)
            except KeyboardInterrupt:
                print("\n")
                self.print_color("Ctrl+C - Tapez 'exit' pour quitter", "yellow")
            except EOFError:
                self.running = False
        self.print_color("\n👋 Au revoir!", "cyan")

if __name__ == "__main__":
    AgentCLI().run()
