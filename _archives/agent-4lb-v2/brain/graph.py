"""
🧠 LangGraph - Graphe Principal
Agent 4LB v2
"""
import logging
from typing import Dict, Any, Optional
from functools import partial

# Note: En production, utiliser langgraph
# from langgraph.graph import StateGraph, END
# Pour l'instant, implémentation simplifiée

from .state import AgentState, create_initial_state, should_continue
from .nodes import think_node, act_node, decide_node, end_node, LLMClient

logger = logging.getLogger(__name__)


class Agent4LBGraph:
    """
    Graphe d'états pour l'Agent 4LB v2
    
    Structure du graphe:
    
        START
          │
          ▼
        THINK ◄──────┐
          │          │
          ▼          │
        DECIDE ──────┤
          │          │
          ▼          │
         ACT ────────┘
          │
          ▼
         END
    """
    
    def __init__(self, tools: Dict[str, callable] = None):
        self.tools = tools or {}
        self.tools_description = self._build_tools_description()
        self.llm = LLMClient()
        
    def _build_tools_description(self) -> str:
        """Construire la description des outils"""
        lines = []
        for name, func in self.tools.items():
            doc = func.__doc__ or "Aucune description"
            doc = doc.split('\n')[0].strip()
            lines.append(f"- **{name}**: {doc}")
        return "\n".join(lines)
    
    def run(self, task: str, verbose: bool = True) -> Dict[str, Any]:
        """
        Exécuter le graphe pour une tâche
        
        Args:
            task: La tâche à accomplir
            verbose: Afficher les étapes
            
        Returns:
            État final avec la réponse
        """
        # Initialiser l'état
        state = create_initial_state(task)
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"🧠 Agent 4LB v2 - Nouvelle tâche")
            print(f"{'='*60}")
            print(f"📋 {task}")
            print(f"{'='*60}\n")
        
        # Boucle principale du graphe
        while should_continue(state):
            # 1. THINK - Réflexion
            state = think_node(state, self.llm, self.tools_description)
            
            if verbose:
                print(f"\n--- Itération {state['iteration']} ---")
                print(f"💭 Pensée: {state['current_thought'][:200]}...")
            
            # 2. DECIDE - Routage
            decision = decide_node(state)
            
            if decision == "end":
                break
                
            # 3. ACT - Exécution (si action en attente)
            if state["pending_action"]:
                if verbose:
                    print(f"🔧 Action: {state['pending_action']['tool']}")
                    
                state = act_node(state, self.tools)
                
                if verbose:
                    result = state["last_action_result"] or ""
                    print(f"📤 Résultat: {result[:300]}...")
        
        # END - Finalisation
        state = end_node(state)
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"✅ Terminé en {state['iteration']} itérations")
            print(f"{'='*60}")
            print(f"\n{state['final_answer']}\n")
        
        return {
            "task_id": state["task_id"],
            "task": state["task"],
            "answer": state["final_answer"],
            "iterations": state["iteration"],
            "status": state["status"],
            "error": state.get("error")
        }


def create_agent_graph(tools: Dict[str, callable] = None) -> Agent4LBGraph:
    """Factory pour créer le graphe"""
    return Agent4LBGraph(tools=tools)


def run_agent(task: str, tools: Dict[str, callable] = None, verbose: bool = True) -> str:
    """Exécuter l'agent pour une tâche"""
    graph = create_agent_graph(tools)
    result = graph.run(task, verbose=verbose)
    return result["answer"]


# === Version avec vrai LangGraph (quand disponible) ===
"""
from langgraph.graph import StateGraph, END

def create_langgraph_agent(tools: Dict[str, callable]):
    '''Créer le graphe avec LangGraph'''
    
    workflow = StateGraph(AgentState)
    
    # Ajouter les nœuds
    workflow.add_node("think", partial(think_node, llm=LLMClient(), tools_desc="..."))
    workflow.add_node("act", partial(act_node, tools=tools))
    workflow.add_node("end", end_node)
    
    # Définir les transitions
    workflow.set_entry_point("think")
    
    workflow.add_conditional_edges(
        "think",
        decide_node,
        {
            "continue": "act",
            "end": "end"
        }
    )
    
    workflow.add_edge("act", "think")
    workflow.add_edge("end", END)
    
    return workflow.compile()
"""
