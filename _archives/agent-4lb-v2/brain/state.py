"""
🧠 État Partagé - LangGraph State
"""
from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime


class Message(TypedDict):
    """Message dans la conversation"""
    role: str  # user, assistant, system, tool
    content: str
    timestamp: str
    tool_name: Optional[str]
    tool_result: Optional[str]


class AgentState(TypedDict):
    """État global de l'agent - partagé entre tous les nœuds"""
    
    # === Tâche courante ===
    task: str                          # Tâche demandée par l'utilisateur
    task_id: str                       # ID unique de la tâche
    
    # === Historique conversation ===
    messages: List[Message]            # Historique des messages
    
    # === État cognitif ===
    current_thought: str               # Réflexion actuelle
    plan: List[str]                    # Plan d'actions
    current_step: int                  # Étape actuelle du plan
    
    # === Actions ===
    pending_action: Optional[Dict[str, Any]]  # Action en attente d'exécution
    last_action_result: Optional[str]         # Résultat de la dernière action
    
    # === Méta ===
    iteration: int                     # Nombre d'itérations
    max_iterations: int                # Limite d'itérations
    status: str                        # pending, running, completed, failed
    error: Optional[str]               # Message d'erreur si échec
    
    # === Mémoire ===
    context: Dict[str, Any]            # Contexte supplémentaire
    memory_recalls: List[str]          # Souvenirs rappelés
    
    # === Résultat ===
    final_answer: Optional[str]        # Réponse finale


def create_initial_state(task: str, task_id: str = None) -> AgentState:
    """Créer l'état initial pour une nouvelle tâche"""
    from uuid import uuid4
    
    return AgentState(
        task=task,
        task_id=task_id or str(uuid4()),
        messages=[
            Message(
                role="user",
                content=task,
                timestamp=datetime.now().isoformat(),
                tool_name=None,
                tool_result=None
            )
        ],
        current_thought="",
        plan=[],
        current_step=0,
        pending_action=None,
        last_action_result=None,
        iteration=0,
        max_iterations=15,
        status="pending",
        error=None,
        context={},
        memory_recalls=[],
        final_answer=None
    )


def should_continue(state: AgentState) -> bool:
    """Vérifier si l'agent doit continuer"""
    if state["status"] in ("completed", "failed"):
        return False
    if state["iteration"] >= state["max_iterations"]:
        return False
    if state["final_answer"] is not None:
        return False
    return True
