"""
Module d'Auto-Apprentissage pour AI Orchestrator v3.0
Extrait automatiquement les faits, préférences et résume les conversations
"""

import re
import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import chromadb
from chromadb.config import Settings

# Désactiver la télémétrie ChromaDB pour éviter l'erreur
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# Patch posthog pour éviter l'erreur "capture() takes 1 positional argument"
try:
    import posthog
    posthog.disabled = True
    posthog.capture = lambda *args, **kwargs: None
except ImportError:
    pass

# Patterns pour détecter les informations importantes
FACT_PATTERNS = [
    # Informations personnelles
    (r"je (?:suis|m'appelle|travaille comme) (.+?)(?:\.|,|$)", "user_fact"),
    (r"mon (?:nom|prénom) (?:est|c'est) (.+?)(?:\.|,|$)", "user_fact"),
    (r"j'(?:ai|habite|vis) (.+?)(?:\.|,|$)", "user_fact"),
    
    # Projets et travail
    (r"je travaille (?:sur|avec) (.+?)(?:\.|,|$)", "project"),
    (r"mon projet (?:actuel|en cours|principal) (?:est|c'est) (.+?)(?:\.|,|$)", "project"),
    (r"je (?:développe|crée|construis) (.+?)(?:\.|,|$)", "project"),
    
    # Préférences
    (r"je (?:préfère|veux|aime) (.+?)(?:\.|,|$)", "preference"),
    (r"j'(?:aime|adore|déteste) (.+?)(?:\.|,|$)", "preference"),
    (r"(?:pas de|sans|évite) (.+?) s'il te plaît", "preference"),
    
    # Faits techniques
    (r"mon serveur (?:a|utilise|tourne sur) (.+?)(?:\.|,|$)", "tech_fact"),
    (r"j'utilise (.+?) pour (.+?)(?:\.|,|$)", "tech_fact"),
    (r"ma (?:config|configuration|stack) (?:est|inclut) (.+?)(?:\.|,|$)", "tech_fact"),
]

# Mots-clés indiquant une correction
CORRECTION_KEYWORDS = [
    "non", "pas", "incorrect", "faux", "erreur", "corrige", "en fait", "plutôt"
]

def get_chroma_collection():
    """Obtenir la collection ChromaDB avec télémétrie désactivée"""
    client = chromadb.HttpClient(
        host="chromadb", 
        port=8000,
        settings=Settings(anonymized_telemetry=False)
    )
    return client.get_or_create_collection(
        name="ai_orchestrator_memory",
        metadata={"description": "Mémoire sémantique avec auto-apprentissage"}
    )

def extract_facts_from_message(message: str) -> List[Dict]:
    """
    Extraire automatiquement les faits d'un message utilisateur
    Retourne une liste de faits avec leur catégorie
    """
    facts = []
    message_lower = message.lower()
    
    for pattern, category in FACT_PATTERNS:
        matches = re.finditer(pattern, message_lower, re.IGNORECASE)
        for match in matches:
            fact_content = match.group(1).strip()
            if len(fact_content) > 3:  # Ignorer les faits trop courts
                facts.append({
                    "content": fact_content,
                    "category": category,
                    "original": match.group(0),
                    "timestamp": datetime.now().isoformat()
                })
    
    return facts

def detect_correction(message: str) -> bool:
    """Détecter si le message contient une correction"""
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in CORRECTION_KEYWORDS)

def extract_problem_solution(conversation: List[Dict]) -> Optional[Dict]:
    """
    Analyser une conversation pour extraire un problème et sa solution
    """
    if len(conversation) < 2:
        return None
    
    # Chercher des patterns de problème/solution
    problem_keywords = ["erreur", "problème", "bug", "marche pas", "fonctionne pas", "aide", "comment"]
    solution_keywords = ["résolu", "corrigé", "fonctionne", "marche", "fixé", "solution"]
    
    problem = None
    solution = None
    
    for msg in conversation:
        text = msg.get("content", "").lower()
        role = msg.get("role", "")
        
        if role == "user" and any(kw in text for kw in problem_keywords):
            problem = msg.get("content", "")[:200]
        
        if role == "assistant" and any(kw in text for kw in solution_keywords):
            solution = msg.get("content", "")[:500]
    
    if problem and solution:
        return {
            "problem": problem,
            "solution": solution,
            "timestamp": datetime.now().isoformat()
        }
    
    return None

def summarize_conversation(conversation: List[Dict]) -> str:
    """
    Créer un résumé de la conversation
    """
    if not conversation:
        return ""
    
    # Extraire les points clés
    user_messages = [m["content"] for m in conversation if m.get("role") == "user"]
    
    if not user_messages:
        return ""
    
    # Résumé simple: premier message + nombre d'échanges
    first_topic = user_messages[0][:100] if user_messages else "Conversation"
    num_exchanges = len(conversation)
    
    summary = f"Conversation ({num_exchanges} messages) - Sujet: {first_topic}"
    
    return summary

def auto_learn_from_message(message: str, conversation_id: str) -> List[str]:
    """
    Fonction principale d'auto-apprentissage
    Analyse un message et stocke les informations apprises
    Retourne la liste des faits appris
    """
    learned = []
    
    try:
        collection = get_chroma_collection()
        
        # Extraire les faits
        facts = extract_facts_from_message(message)
        
        for fact in facts:
            # Créer un ID unique pour ce fait
            fact_id = f"auto_{fact['category']}_{hash(fact['content']) % 10000}"
            
            # Stocker dans ChromaDB
            doc_content = f"{fact['category']}: {fact['content']}"
            
            collection.upsert(
                documents=[doc_content],
                ids=[fact_id],
                metadatas=[{
                    "category": fact["category"],
                    "type": "auto_learned",
                    "source": "conversation",
                    "conversation_id": conversation_id,
                    "timestamp": fact["timestamp"]
                }]
            )
            
            learned.append(f"[{fact['category']}] {fact['content']}")
        
        return learned
    
    except Exception as e:
        print(f"Erreur auto-apprentissage: {e}")
        return []

def save_conversation_summary(conversation: List[Dict], conversation_id: str) -> bool:
    """
    Sauvegarder le résumé d'une conversation terminée
    """
    try:
        collection = get_chroma_collection()
        
        summary = summarize_conversation(conversation)
        if not summary:
            return False
        
        # Extraire problème/solution si présent
        problem_solution = extract_problem_solution(conversation)
        
        # Sauvegarder le résumé
        collection.upsert(
            documents=[f"conversation_summary: {summary}"],
            ids=[f"conv_{conversation_id}"],
            metadatas=[{
                "type": "conversation_summary",
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat(),
                "has_solution": problem_solution is not None
            }]
        )
        
        # Sauvegarder la solution si trouvée
        if problem_solution:
            collection.upsert(
                documents=[f"solved_issue: {problem_solution['problem']} → {problem_solution['solution']}"],
                ids=[f"solution_{conversation_id}"],
                metadatas=[{
                    "type": "solved_issue",
                    "conversation_id": conversation_id,
                    "timestamp": problem_solution["timestamp"]
                }]
            )
        
        return True
    
    except Exception as e:
        print(f"Erreur sauvegarde résumé: {e}")
        return False

def get_relevant_context(query: str, limit: int = 5) -> List[str]:
    """
    Récupérer le contexte pertinent pour une nouvelle requête
    """
    try:
        collection = get_chroma_collection()
        
        # Recherche sémantique
        results = collection.query(
            query_texts=[query],
            n_results=limit,
            include=["documents", "metadatas", "distances"]
        )
        
        context = []
        if results and results.get("documents") and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                mem_type = meta.get("type", "unknown")
                category = meta.get("category", "")
                
                # Formater selon le type
                if mem_type == "auto_learned":
                    context.append(f"📝 [Appris] {doc}")
                elif mem_type == "solved_issue":
                    context.append(f"✅ [Solution passée] {doc}")
                elif mem_type == "conversation_summary":
                    context.append(f"💬 [Historique] {doc}")
                else:
                    context.append(f"🧠 {doc}")
        
        return context
    
    except Exception as e:
        print(f"Erreur récupération contexte: {e}")
        return []

def get_user_preferences() -> Dict:
    """
    Récupérer les préférences utilisateur stockées
    """
    try:
        collection = get_chroma_collection()
        
        # Chercher les préférences
        results = collection.get(
            where={"category": "preference"},
            limit=10,
            include=["documents", "metadatas"]
        )
        
        preferences = {}
        if results and results.get("documents"):
            for doc in results["documents"]:
                # Parser le document
                if ":" in doc:
                    key, value = doc.split(":", 1)
                    preferences[key.strip()] = value.strip()
        
        return preferences
    
    except Exception as e:
        print(f"Erreur récupération préférences: {e}")
        return {}

def get_memory_stats() -> Dict:
    """
    Obtenir les statistiques de la mémoire
    """
    try:
        collection = get_chroma_collection()
        
        all_data = collection.get(include=["metadatas"])
        
        stats = {
            "total": len(all_data.get("ids", [])),
            "by_type": {},
            "by_category": {}
        }
        
        for meta in all_data.get("metadatas", []):
            mem_type = meta.get("type", "unknown")
            category = meta.get("category", "unknown")
            
            stats["by_type"][mem_type] = stats["by_type"].get(mem_type, 0) + 1
            if category != "unknown":
                stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
        
        return stats
    
    except Exception as e:
        return {"error": str(e)}
