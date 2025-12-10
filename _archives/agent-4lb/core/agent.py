"""
🧠 Agent Autonome 4LB - Cœur du système
"""
import json
import re
from datetime import datetime
from typing import Optional, List, Dict
import logging
import requests

from core.config import (OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TEMPERATURE,
    ANTHROPIC_API_KEY, CLAUDE_MODEL, DEFAULT_LLM, AGENT_MAX_ITERATIONS, AGENT_NAME)
from tools.system_tools import TOOLS, get_tools_description

logger = logging.getLogger(__name__)

class Agent4LB:
    """Agent autonome capable d'exécuter des tâches complexes"""
    
    def __init__(self, llm: str = None):
        self.llm = llm or DEFAULT_LLM
        self.tools = TOOLS
        self.conversation_history: List[Dict] = []
        self.current_task: Optional[str] = None
        self.iteration_count = 0
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        tools_desc = get_tools_description()
        return f"""Tu es {AGENT_NAME}, un agent IA autonome expert en administration système, DevOps et infrastructure.

Tu as accès aux outils suivants:
{tools_desc}

## Format d'action
Pour utiliser un outil, réponds avec ce JSON:
```json
{{"thought": "Ta réflexion", "action": "nom_outil", "action_input": {{"param": "valeur"}}}}
```

## Quand terminé
```json
{{"thought": "Résumé", "action": "final_answer", "action_input": {{"answer": "Réponse finale"}}}}
```

## Règles
1. UNE seule action par réponse
2. Vérifier chaque résultat avant de continuer
3. S'auto-corriger en cas d'erreur
4. Ne jamais inventer de résultats

## Contexte
- Serveur: lalpha-server-1 (Ubuntu 25.10)
- GPU: NVIDIA RTX 5070 Ti (16GB)
- Ollama: localhost:11434
- Infrastructure: /home/lalpha/projets/infrastructure/4lb-docker-stack/
"""
    
    def _call_ollama(self, messages: List[Dict]) -> str:
        try:
            prompt = ""
            for msg in messages:
                role, content = msg["role"], msg["content"]
                if role == "system": prompt += f"System: {content}\n\n"
                elif role == "user": prompt += f"User: {content}\n\n"
                elif role == "assistant": prompt += f"Assistant: {content}\n\n"
            prompt += "Assistant: "
            
            response = requests.post(f"{OLLAMA_HOST}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                      "options": {"temperature": OLLAMA_TEMPERATURE}}, timeout=120)
            
            return response.json().get("response", "") if response.status_code == 200 else f"Erreur: {response.status_code}"
        except Exception as e:
            return f"Erreur Ollama: {str(e)}"
    
    def _call_claude(self, messages: List[Dict]) -> str:
        if not ANTHROPIC_API_KEY: return "Erreur: ANTHROPIC_API_KEY non configurée"
        try:
            system_msg = ""
            chat_messages = []
            for msg in messages:
                if msg["role"] == "system": system_msg = msg["content"]
                else: chat_messages.append({"role": msg["role"], "content": msg["content"]})
            
            response = requests.post("https://api.anthropic.com/v1/messages",
                headers={"Content-Type": "application/json", "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01"},
                json={"model": CLAUDE_MODEL, "max_tokens": 4096, "system": system_msg,
                      "messages": chat_messages}, timeout=60)
            
            return response.json()["content"][0]["text"] if response.status_code == 200 else f"Erreur: {response.status_code}"
        except Exception as e:
            return f"Erreur Claude: {str(e)}"
    
    def _call_llm(self, messages: List[Dict]) -> str:
        return self._call_claude(messages) if self.llm == "claude" else self._call_ollama(messages)
    
    def _parse_action(self, response: str) -> Optional[Dict]:
        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match: json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{[\s\S]*"action"[\s\S]*\}', response)
                if json_match: json_str = json_match.group(0)
                else: return None
            action_data = json.loads(json_str)
            return action_data if "action" in action_data else None
        except: return None
    
    def _execute_action(self, action: str, action_input: Dict) -> str:
        if action == "final_answer": return action_input.get("answer", "Tâche terminée")
        if action not in self.tools:
            return f"Erreur: Outil '{action}' non trouvé. Disponibles: {list(self.tools.keys())}"
        try:
            return self.tools[action](**action_input)
        except Exception as e:
            return f"Erreur {action}: {str(e)}"
    
    def run(self, task: str, verbose: bool = True) -> str:
        """Exécuter une tâche de manière autonome"""
        self.current_task, self.iteration_count = task, 0
        messages = [{"role": "system", "content": self.system_prompt},
                   {"role": "user", "content": f"Tâche: {task}"}]
        
        if verbose:
            print(f"\n{'='*60}\n🧠 {AGENT_NAME} - Nouvelle tâche\n{'='*60}\n📋 {task}\n{'='*60}\n")
        
        while self.iteration_count < AGENT_MAX_ITERATIONS:
            self.iteration_count += 1
            if verbose: print(f"\n--- Itération {self.iteration_count}/{AGENT_MAX_ITERATIONS} ---")
            
            response = self._call_llm(messages)
            if verbose: print(f"\n🤖 Réponse:\n{response[:500]}...")
            
            action_data = self._parse_action(response)
            if not action_data:
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": "Réponds avec JSON: thought, action, action_input"})
                continue
            
            thought = action_data.get("thought", "")
            action = action_data.get("action", "")
            action_input = action_data.get("action_input", {})
            
            if verbose:
                print(f"\n💭 Pensée: {thought}\n🔧 Action: {action}\n📥 Input: {json.dumps(action_input, indent=2)}")
            
            if action == "final_answer":
                final = action_input.get("answer", "Terminé")
                if verbose: print(f"\n{'='*60}\n✅ Terminé en {self.iteration_count} itérations\n{'='*60}\n\n{final}")
                return final
            
            result = self._execute_action(action, action_input)
            if verbose: print(f"\n📤 Résultat:\n{result[:1000]}...")
            
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"Résultat de '{action}':\n{result}\n\nContinue ou donne la réponse finale."})
        
        return f"⚠️ Limite de {AGENT_MAX_ITERATIONS} itérations"
    
    def chat(self, message: str) -> str:
        """Mode conversation"""
        self.conversation_history.append({"role": "user", "content": message})
        messages = [{"role": "system", "content": self.system_prompt}] + self.conversation_history[-20:]
        response = self._call_llm(messages)
        self.conversation_history.append({"role": "assistant", "content": response})
        return response
    
    def reset(self):
        self.conversation_history, self.current_task, self.iteration_count = [], None, 0

agent = Agent4LB()

def run_task(task: str, verbose: bool = True, llm: str = None) -> str:
    return Agent4LB(llm=llm).run(task, verbose=verbose) if llm else agent.run(task, verbose=verbose)
