"""
Outils IA pour AI Orchestrator v4.0
- analyze_image: Analyse d'images avec modèle vision
- create_plan: Création de plans d'action
- final_answer: Réponse finale à l'utilisateur
"""

import base64
import logging
import os

import httpx

from tools import register_tool

logger = logging.getLogger(__name__)

# Configuration Ollama
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
VISION_MODEL = os.getenv("VISION_MODEL", "llama3.2-vision:11b")


@register_tool("analyze_image")
async def analyze_image(params: dict, uploaded_files: dict = None) -> str:
    """
    Analyser une image avec un modèle de vision.

    Args:
        query: Question ou instruction pour l'analyse
        uploaded_files: Dictionnaire des fichiers uploadés
    """
    query = params.get("query", "Décris cette image en détail")

    if not uploaded_files:
        return "⚠️ Aucune image fournie. Uploadez une image pour l'analyser."

    # Trouver la première image
    image_data = None
    image_name = None

    for file_id, file_info in uploaded_files.items():
        if file_info.get("mime_type", "").startswith("image/"):
            try:
                file_path = file_info.get("path")
                if file_path and os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        image_data = base64.b64encode(f.read()).decode("utf-8")
                    image_name = file_info.get("filename", file_id)
                    break
            except Exception as e:
                logger.error(f"Erreur lecture image: {e}")

    if not image_data:
        return "❌ Impossible de lire l'image uploadée"

    try:
        # Appel à Ollama avec le modèle vision
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": VISION_MODEL,
                    "prompt": query,
                    "images": [image_data],
                    "stream": False,
                },
            )

            if response.status_code == 200:
                result = response.json()
                analysis = result.get("response", "Analyse non disponible")
                return f"🖼️ Analyse de {image_name}:\n\n{analysis}"
            else:
                return f"❌ Erreur API vision: {response.status_code}"

    except httpx.TimeoutException:
        return "⏱️ Timeout lors de l'analyse (image trop complexe?)"
    except Exception as e:
        logger.error(f"Erreur analyze_image: {e}")
        return f"❌ Erreur: {str(e)}"


@register_tool("create_plan")
async def create_plan(params: dict) -> str:
    """
    Créer un plan d'action structuré.

    Args:
        objective: Objectif à atteindre
        constraints: Contraintes à respecter (optionnel)
    """
    objective = params.get("objective", "")
    constraints = params.get("constraints", "")

    if not objective:
        return "Erreur: objectif requis pour créer un plan"

    # Construire le plan
    plan_lines = [
        "📋 PLAN D'ACTION",
        "=" * 50,
        "",
        f"🎯 Objectif: {objective}",
    ]

    if constraints:
        plan_lines.append(f"⚠️ Contraintes: {constraints}")

    plan_lines.extend(
        [
            "",
            "📌 Étapes suggérées:",
            "1. Analyser la situation actuelle",
            "2. Identifier les ressources nécessaires",
            "3. Exécuter les actions",
            "4. Vérifier les résultats",
            "5. Documenter les changements",
            "",
            "⏭️ Prochaine action: Commencer par l'étape 1",
        ]
    )

    return "\n".join(plan_lines)


@register_tool("final_answer")
async def final_answer(params: dict) -> str:
    """
    Fournir la réponse finale à l'utilisateur.
    C'est l'outil de conclusion obligatoire.

    Args:
        answer: La réponse complète et formatée
    """
    answer = params.get("answer", "")

    if not answer:
        return "⚠️ Réponse vide"

    # La réponse est retournée telle quelle
    # Le traitement du format est fait dans la boucle ReAct
    return answer


@register_tool("summarize")
async def summarize(params: dict) -> str:
    """
    Résumer un texte long.

    Args:
        text: Texte à résumer
        max_length: Longueur max du résumé (optionnel)
    """
    text = params.get("text", "")
    max_length = params.get("max_length", 500)

    if not text:
        return "Erreur: texte requis"

    # Pour un résumé simple, on peut tronquer intelligemment
    # ou utiliser un modèle LLM

    if len(text) <= max_length:
        return f"📝 Résumé:\n{text}"

    # Résumé basique: premières phrases + dernières phrases
    sentences = text.split(". ")
    if len(sentences) <= 4:
        return f"📝 Résumé:\n{text[:max_length]}..."

    summary = ". ".join(sentences[:2]) + "... " + ". ".join(sentences[-2:])
    return f"📝 Résumé:\n{summary}"


@register_tool("web_search")
async def web_search(params: dict) -> str:
    """
    Recherche web (placeholder - nécessite une API externe)

    Args:
        query: Requête de recherche
    """
    query = params.get("query", "")

    if not query:
        return "Erreur: requête de recherche requise"

    # Placeholder - à implémenter avec DuckDuckGo, Searx, etc.
    return f"🔍 Recherche web pour '{query}':\n⚠️ Fonctionnalité non implémentée. Utilisez execute_command avec curl pour des recherches spécifiques."
