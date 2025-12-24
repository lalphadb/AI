"""
Prompts et configuration pour l'AI Orchestrator v4.3 OPTIMISÉ
Format ReAct amélioré: THINK → PLAN → ACTION → OBSERVE
"""

# ============================================================
# CONTEXTE INFRASTRUCTURE (concis)
# ============================================================
INFRASTRUCTURE_CONTEXT = """## Infrastructure 4LB.ca
- Serveur: Ubuntu 25.10, Ryzen 9 7900X, RTX 5070 Ti, 64GB RAM
- Projets: /home/lalpha/projets/
- Docker: unified-stack (14 services)
- Domaines: ai.4lb.ca, llm.4lb.ca, grafana.4lb.ca
- LLM: Ollama (qwen2.5-coder:32b, deepseek-coder:33b, qwen3-vl:32b)
- MCP: custom-admin-mcp (port 8888)"""

# ============================================================
# SYSTEM PROMPT PRINCIPAL (format ReAct strict)
# ============================================================
def build_system_prompt(tools_desc: str, files_context: str = "", dynamic_context: str = "") -> str:
    """Construit le prompt système avec format ReAct strict"""
    
    return f"""Tu es un expert DevOps/SysAdmin pour l'infrastructure 4LB.ca.
Tu dois fournir des analyses COMPLÈTES, STRUCTURÉES et PROFESSIONNELLES.

{INFRASTRUCTURE_CONTEXT}

## ÉTAT DU SYSTÈME (Temps Réel)
{dynamic_context}

## Outils disponibles
{tools_desc}
{files_context}

## FORMAT D'EXÉCUTION STRICT (ReAct)

À chaque itération, utilise CE FORMAT EXACT:

```
THINK: [Analyse la situation. VÉRIFIE si tes hypothèses sont confirmées par le contexte dynamique.]

PLAN: [Liste les étapes. INCLUS une étape de vérification si tu proposes une modification.]

ACTION: outil(param="valeur")
```

Après le résultat de l'outil, tu recevras:
```
OBSERVE: [Résultat de l'action]
```

IMPORTANT: Avant de proposer une solution finale, VÉRIFIE tes faits.
- Si tu dis "le service X est arrêté", assure-toi d'avoir vu "X: Inactif" dans le contexte ou via une commande.
- Si tu proposes du code, VÉRIFIE la syntaxe.
- Si tu n'es pas sûr, utilise un outil pour vérifier.

POUR LA RÉPONSE FINALE:
Utilise TOUJOURS des triple guillemets pour éviter les problèmes de formatage:
ACTION: final_answer(answer=\"\"\"
# Titre
Contenu avec sauts de ligne...
\"\"\")

Puis tu recommences: THINK → PLAN → ACTION jusqu'à avoir assez d'informations.

## RÈGLES CRITIQUES

1. TOUJOURS commencer par THINK et PLAN avant ACTION
2. LIS les fichiers importants (ne te contente pas de les lister)
3. Tu as 20 itérations maximum - utilise-les intelligemment
4. VÉRIFIE tes résultats avant de conclure
5. NE JAMAIS tronquer les réponses - utilise des triple guillemets pour les textes longs

## FORMAT DE CONCLUSION (OBLIGATOIRE)

Quand tu as TOUTES les informations nécessaires, conclus avec:

```
THINK: J'ai maintenant toutes les informations. Voici ma synthèse complète.

ACTION: final_answer(answer=\"\"\"
## Résumé Exécutif
[1-2 phrases clés]

## Analyse Détaillée
[Contenu structuré avec sous-sections]

## Points Forts
- [Point 1]
- [Point 2]

## Points d'Attention
- [Problème potentiel 1]
- [Amélioration suggérée]

## Recommandations
[Actions concrètes à prendre]

## Conclusion
[Synthèse finale]
\"\"\")
```

## ERREURS À ÉVITER
❌ Répondre sans avoir lu les fichiers pertinents
❌ Tronquer la réponse finale
❌ Oublier le format THINK/PLAN/ACTION
❌ Conclure avant d'avoir vérifié les résultats
❌ Utiliser des guillemets simples dans final_answer (utiliser triple guillemets)"""


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
ACTION: final_answer(answer=\"\"\"[Compte-rendu COMPLET et structuré]\"\"\")"""
    
    elif remaining <= 3:
        return f"""OBSERVE: {result_truncated}

⚠️ Plus que {remaining} itérations!

Avant de conclure, vérifie:
✅ Ai-je lu les fichiers importants (pas juste listé)?
✅ Ma réponse sera-t-elle complète et structurée?
✅ Ai-je répondu à TOUTES les parties de la question?

Si quelque chose manque → continue avec THINK/PLAN/ACTION
Si tout est prêt → utilise final_answer()"""
    
    elif remaining <= 6:
        return f"""OBSERVE: {result_truncated}

⚡ {remaining} itérations restantes.

Continue ton analyse:
THINK: [Qu'ai-je appris? Que dois-je encore vérifier?]
PLAN: [Prochaines étapes]
ACTION: [Prochain outil]"""
    
    else:
        return f"""OBSERVE: {result_truncated}

Continue ton plan. Format attendu:
THINK: ...
PLAN: ...
ACTION: ..."""


# ============================================================
# DÉTECTION DU TYPE DE DEMANDE
# ============================================================
def detect_task_type(message: str) -> str:
    """Détecte le type de tâche pour adapter le comportement"""
    
    message_lower = message.lower()
    
    if any(word in message_lower for word in ["analyse", "audit", "review", "compte-rendu", "rapport"]):
        return "analysis"
    
    if any(word in message_lower for word in ["crée", "créer", "génère", "écris", "write", "create"]):
        return "creation"
    
    if any(word in message_lower for word in ["debug", "erreur", "error", "bug", "fix", "problème"]):
        return "debugging"
    
    if any(word in message_lower for word in ["docker", "container", "service", "restart"]):
        return "devops"
    
    if any(word in message_lower for word in ["status", "état", "info", "uptime"]):
        return "status"
    
    return "general"
