"""
🧩 Nœuds du Graphe - LangGraph Nodes
"""
import json
import re
import logging
from typing import Dict, Any, Literal
from datetime import datetime

from .state import AgentState, Message
from .prompts import SYSTEM_PROMPT, THINK_PROMPT, OBSERVE_PROMPT

logger = logging.getLogger(__name__)


class LLMClient:
    """Client LLM unifié (Ollama + Claude)"""
    
    def __init__(self, provider: str = "ollama"):
        self.provider = provider
        self.ollama_host = "http://localhost:11434"
        self.ollama_model = "qwen2.5-coder:32b-instruct-q4_K_M"
        
    def call(self, messages: list[Dict], tools_desc: str = "") -> str:
        """Appeler le LLM"""
        import requests
        
        # Construire le prompt
        system = SYSTEM_PROMPT.format(tools_description=tools_desc)
        prompt = f"System: {system}\n\n"
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt += f"{role.capitalize()}: {content}\n\n"
        prompt += "Assistant: "
        
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1}
                },
                timeout=120
            )
            if response.status_code == 200:
                return response.json().get("response", "")
            return f"Erreur LLM: {response.status_code}"
        except Exception as e:
            return f"Erreur: {str(e)}"


def parse_llm_response(response: str) -> Dict[str, Any]:
    """Parser la réponse JSON du LLM"""
    try:
        # Chercher le JSON dans la réponse
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'\{[\s\S]*"type"[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group(0)
            else:
                return {"type": "error", "error": "No JSON found"}
        
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        return {"type": "error", "error": f"JSON parse error: {e}"}


# === NŒUDS DU GRAPHE ===

def think_node(state: AgentState, llm: LLMClient, tools_desc: str) -> AgentState:
    """
    🧠 Nœud THINK - Réflexion et planification
    """
    state["iteration"] += 1
    state["status"] = "running"
    
    # Préparer les messages
    messages = [{"role": m["role"], "content": m["content"]} for m in state["messages"]]
    
    # Ajouter contexte si c'est une continuation
    if state["last_action_result"]:
        messages.append({
            "role": "user",
            "content": f"Résultat de la dernière action:\n{state['last_action_result']}\n\nContinue ou termine."
        })
    
    # Appeler le LLM
    response = llm.call(messages, tools_desc)
    parsed = parse_llm_response(response)
    
    # Mettre à jour l'état
    state["current_thought"] = parsed.get("thought", "")
    
    if parsed.get("type") == "think":
        state["plan"] = parsed.get("plan", [])
    elif parsed.get("type") == "action":
        state["pending_action"] = {
            "tool": parsed.get("tool"),
            "input": parsed.get("input", {})
        }
    elif parsed.get("type") == "final":
        state["final_answer"] = parsed.get("answer", "")
        state["status"] = "completed"
    
    # Ajouter à l'historique
    state["messages"].append(Message(
        role="assistant",
        content=response,
        timestamp=datetime.now().isoformat(),
        tool_name=None,
        tool_result=None
    ))
    
    logger.info(f"[THINK] Iteration {state['iteration']}: {state['current_thought'][:100]}...")
    return state


def act_node(state: AgentState, tools: Dict[str, callable]) -> AgentState:
    """
    ⚡ Nœud ACT - Exécution des outils
    """
    if not state["pending_action"]:
        logger.warning("[ACT] No pending action")
        return state
    
    tool_name = state["pending_action"]["tool"]
    tool_input = state["pending_action"]["input"]
    
    logger.info(f"[ACT] Executing: {tool_name}({tool_input})")
    
    try:
        if tool_name not in tools:
            result = f"Erreur: Outil '{tool_name}' non trouvé. Disponibles: {list(tools.keys())}"
        else:
            tool_func = tools[tool_name]
            result = tool_func(**tool_input)
    except Exception as e:
        result = f"Erreur d'exécution: {str(e)}"
    
    # Mettre à jour l'état
    state["last_action_result"] = result
    state["pending_action"] = None
    
    # Ajouter à l'historique
    state["messages"].append(Message(
        role="tool",
        content=result[:5000],  # Limiter la taille
        timestamp=datetime.now().isoformat(),
        tool_name=tool_name,
        tool_result=result[:1000]
    ))
    
    logger.info(f"[ACT] Result: {result[:200]}...")
    return state


def observe_node(state: AgentState) -> AgentState:
    """
    👁️ Nœud OBSERVE - Analyse des résultats
    (Souvent fusionné avec THINK dans une implémentation simple)
    """
    # L'observation est gérée dans think_node via last_action_result
    return state


def decide_node(state: AgentState) -> Literal["continue", "end"]:
    """
    🔀 Nœud DECIDE - Routage conditionnel
    """
    if state["status"] == "completed":
        return "end"
    if state["status"] == "failed":
        return "end"
    if state["iteration"] >= state["max_iterations"]:
        state["status"] = "failed"
        state["error"] = f"Limite de {state['max_iterations']} itérations atteinte"
        return "end"
    if state["final_answer"]:
        return "end"
    if state["pending_action"]:
        return "continue"
    return "continue"


def end_node(state: AgentState) -> AgentState:
    """
    🏁 Nœud END - Finalisation
    """
    if not state["final_answer"] and state["status"] != "completed":
        state["final_answer"] = f"Tâche terminée après {state['iteration']} itérations."
    
    logger.info(f"[END] Status: {state['status']}, Answer: {state['final_answer'][:100]}...")
    return state
