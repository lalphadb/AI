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

## ⚠️ LIMITATIONS (P1-1)
Certaines commandes sont interdites pour raisons de sécurité:
- mkfs, fdisk, parted, dd (manipulation disques)
- rm -rf / (destruction système)
- Patterns de fork bomb

Si une commande est bloquée (🚫), tu recevras un message explicite.
→ EXPLIQUE la raison à l'utilisateur
→ PROPOSE une alternative sûre si possible

## ERREURS À ÉVITER
❌ Répondre sans avoir lu les fichiers pertinents
❌ Oublier le format THINK/PLAN/ACTION
❌ Ne pas mémoriser les informations importantes apprises
❌ Affirmer des faits sans vérification (P2: toujours vérifier!)

## 🎯 HONNÊTETÉ ET INCERTITUDE (P2)
Tu dois être HONNÊTE sur ce que tu sais et ne sais pas:
- Si tu n'es PAS SÛR d'une information → DIS-LE: "Je ne suis pas certain..."
- Si tu ne trouves PAS de données → DIS-LE: "Je n'ai pas trouvé..."
- Si une commande échoue → EXPLIQUE clairement l'échec
- JAMAIS inventer ou supposer des données
- Préfère "je vais vérifier" à une réponse incertaine
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
    if any(word in message_lower for word in ["analyse", "audit", "review"]):
        return "analysis"
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


# ============================================================
# P1-2: ROUTER FACTUEL VS OPÉRATIONNEL
# ============================================================
def classify_query(message: str) -> str:
    """
    P1-2: Classifie une requête comme 'factual' ou 'operational'
    - factual: Questions de connaissance générale, définitions, explications
    - operational: Requêtes nécessitant des outils (commandes, fichiers, système)

    Returns: "factual" ou "operational"
    """
    message_lower = message.lower().strip()

    # Keywords indiquant une requête opérationnelle
    OPERATIONAL_KEYWORDS = [
        # Actions système
        "uptime",
        "status",
        "état",
        "disk",
        "disque",
        "cpu",
        "ram",
        "mémoire",
        "container",
        "docker",
        "service",
        "process",
        "processus",
        # Actions fichiers
        "fichier",
        "file",
        "dossier",
        "folder",
        "répertoire",
        "directory",
        "lis",
        "read",
        "ouvre",
        "open",
        "affiche",
        "show",
        "liste",
        "list",
        "crée",
        "create",
        "écris",
        "write",
        "modifie",
        "edit",
        "supprime",
        "delete",
        # Actions réseau
        "réseau",
        "network",
        "ip",
        "port",
        "connexion",
        "connection",
        # Actions spécifiques à l'infra
        "serveur",
        "server",
        "mon",
        "mes",
        "notre",
        "nos",
        # Verbes d'action
        "vérifie",
        "check",
        "analyse",
        "analyze",
        "scanne",
        "scan",
        "exécute",
        "execute",
        "lance",
        "run",
        "démarre",
        "start",
        "arrête",
        "stop",
        # Référence à l'infrastructure
        "4lb",
        "lalpha",
        "projets",
        "traefik",
        "nginx",
        "ollama",
    ]

    # Keywords indiquant une question factuelle
    FACTUAL_KEYWORDS = [
        "qu'est-ce",
        "c'est quoi",
        "définition",
        "definition",
        "explique",
        "explain",
        "comment fonctionne",
        "how does",
        "pourquoi",
        "why",
        "différence entre",
        "difference between",
        "avantages",
        "advantages",
        "inconvénients",
        "disadvantages",
        "meilleure pratique",
        "best practice",
        "recommand",
        "histoire de",
        "history of",
        "origine",
        "origin",
    ]

    # Patterns explicites opérationnels
    OPERATIONAL_PATTERNS = [
        r"^(lis|affiche|montre|vérifie|check|analyse|scanne)\s",
        r"(de mon|du serveur|de l'infra|sur le système)",
        r"(docker ps|docker logs|systemctl|journalctl)",
    ]

    import re

    # 1. Vérifier patterns explicites opérationnels
    for pattern in OPERATIONAL_PATTERNS:
        if re.search(pattern, message_lower):
            return "operational"

    # 2. Compter les keywords
    operational_score = sum(1 for kw in OPERATIONAL_KEYWORDS if kw in message_lower)
    factual_score = sum(1 for kw in FACTUAL_KEYWORDS if kw in message_lower)

    # 3. Décision
    if factual_score > 0 and operational_score == 0:
        return "factual"
    elif operational_score > factual_score:
        return "operational"
    else:
        # Par défaut, considérer comme opérationnel pour ne pas manquer des actions
        return "operational"


def get_factual_prompt() -> str:
    """Prompt pour réponses factuelles (sans outils)"""
    return """Tu es un expert technique qui répond aux questions de connaissance générale.

IMPORTANT: Cette question est FACTUELLE. Tu n'as PAS besoin d'outils pour y répondre.
Réponds directement avec tes connaissances.

Si tu n'es pas sûr de la réponse, dis-le clairement: "Je ne suis pas certain..."

FORMAT DE RÉPONSE:
- Réponds de manière structurée et claire
- Utilise des exemples si pertinent
- Reste concis mais complet

Termine TOUJOURS avec: ACTION: final_answer(answer='''[ta réponse]''')"""
