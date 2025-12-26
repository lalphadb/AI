"""
Prompts et configuration pour l'AI Orchestrator v4.0
Format ReAct amélioré: THINK → PLAN → ACTION → OBSERVE
Avec mémoire sémantique et contexte temporel
"""

from datetime import datetime

# ============================================================
# CONTEXTE INFRASTRUCTURE (concis)
# ============================================================
INFRASTRUCTURE_CONTEXT = """## Infrastructure 4LB.ca
- Serveur: Ubuntu 25.10, Ryzen 9 7900X, RTX 5070 Ti 16GB, 64GB RAM
- Projets: /home/lalpha/projets/
- Docker: unified-stack (14 services) - Gérer avec ./stack.sh
- Domaines: ai.4lb.ca, llm.4lb.ca, grafana.4lb.ca
- LLM: Ollama (qwen2.5-coder:32b, deepseek-coder:33b, qwen3-vl:32b)
- Mémoire: ChromaDB (mémoire sémantique persistante)"""

# ============================================================
# SYSTEM PROMPT PRINCIPAL (format ReAct strict + mémoire)
# ============================================================
def build_system_prompt(tools_desc: str, files_context: str = "", dynamic_context: str = "") -> str:
    """Construit le prompt système avec format ReAct strict et mémoire"""
    
    # Timestamp actuel
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Partie statique (définie ici pour éviter les erreurs de f-string)
    instructions = """
## FORMAT D'EXÉCUTION STRICT (ReAct)

À chaque itération, utilise CE FORMAT EXACT:

THINK: [Analyse la situation. Rappelle-toi du contexte mémorisé si pertinent.]
PLAN: [Liste les étapes.]
ACTION: outil(param="valeur")

Après le résultat de l'outil, tu recevras:
OBSERVE: [Résultat de l'action]

POUR LA RÉPONSE FINALE:
Utilise TOUJOURS des triple guillemets pour éviter les problèmes de formatage:
ACTION: final_answer(answer='''
# Titre
Contenu avec sauts de ligne...
''')

## RÈGLES CRITIQUES
1. TOUJOURS commencer par THINK et PLAN avant ACTION
2. VÉRIFIE tes résultats avant de conclure
3. UTILISE LA MÉMOIRE: rappelle-toi du contexte au début

## ERREURS À ÉVITER
❌ Répondre sans avoir lu les fichiers pertinents
❌ Oublier le format THINK/PLAN/ACTION
❌ Ne pas mémoriser les informations importantes apprises
"""

    return f"""Tu es un expert DevOps/SysAdmin pour l'infrastructure 4LB.ca.
Tu dois fournir des analyses COMPLÈTES, STRUCTURÉES et PROFESSIONNELLES.

{INFRASTRUCTURE_CONTEXT}

## ⏰ CONTEXTE TEMPOREL
Date/Heure actuelle: {now}

## 🧠 MÉMOIRE PERSISTANTE
Tu as une mémoire sémantique (ChromaDB).
- Utilise memory_recall(query="contexte") au début.
- Utilise memory_store(...) pour mémoriser les faits importants.

## ÉTAT DU SYSTÈME (Temps Réel)
{dynamic_context}

## Outils disponibles
{tools_desc}
{files_context}

{instructions}
"""


# ============================================================
# MESSAGES D'URGENCE PROGRESSIFS
# ============================================================
def get_urgency_message(iteration: int, max_iterations: int, result: str) -> str:
    """Retourne un message adapté avec format OBSERVE"""
    
    remaining = max_iterations - iteration
    result_truncated = result[:2000] if len(result) > 2000 else result
    
    if remaining <= 1:
        return f"""OBSERVE: {result_truncated}

🚨 DERNIÈRE ITÉRATION! Tu DOIS conclure MAINTENANT.

THINK: [Synthétise TOUT ce que tu as découvert]
ACTION: final_answer(answer='''[Compte-rendu COMPLET et structuré]''')"""
    
    elif remaining <= 3:
        return f"""OBSERVE: {result_truncated}

⚠️ Plus que {remaining} itérations!
Si tout est prêt → utilise final_answer()"""
    
    else:
        return f"""OBSERVE: {result_truncated}

Continue ton plan."""


# ============================================================
# DÉTECTION DU TYPE DE DEMANDE
# ============================================================
def detect_task_type(message: str) -> str:
    """Détecte le type de tâche pour adapter le comportement"""
    message_lower = message.lower()
    if any(word in message_lower for word in ["analyse", "audit", "review"]): return "analysis"
    return "general"


# ============================================================
# PROMPT INITIAL AVEC MÉMOIRE
# ============================================================
def get_initial_memory_prompt() -> str:
    """Prompt pour rappeler le contexte en début de conversation"""
    return """THINK: C'est une nouvelle conversation. Je vais d'abord vérifier ma mémoire pour le contexte.
ACTION: memory_recall(query="contexte utilisateur projets préférences")"""

# Flag pour indiquer que le module est chargé
PROMPTS_ENABLED = True