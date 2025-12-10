"""
🤖 Outils LLM - LangChain Tools
"""
import requests
from .system import execute_command

OLLAMA_HOST = "http://localhost:11434"


def ollama_list() -> str:
    """Lister les modèles Ollama installés."""
    return execute_command("ollama list")


def ollama_run(model: str, prompt: str, timeout: int = 120) -> str:
    """Exécuter un prompt avec Ollama."""
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=timeout
        )
        if response.status_code == 200:
            return response.json().get("response", "Pas de réponse")
        return f"Erreur Ollama: {response.status_code}"
    except Exception as e:
        return f"Erreur: {str(e)}"


def ollama_pull(model: str) -> str:
    """Télécharger un modèle Ollama."""
    return execute_command(f"ollama pull {model}", timeout=600)


def ollama_rm(model: str) -> str:
    """Supprimer un modèle Ollama."""
    return execute_command(f"ollama rm {model}")


def ollama_show(model: str) -> str:
    """Afficher les informations d'un modèle."""
    return execute_command(f"ollama show {model}")


def ollama_ps() -> str:
    """Lister les modèles en cours d'exécution."""
    return execute_command("ollama ps")


def ollama_chat(model: str, messages: list, timeout: int = 120) -> str:
    """Chat avec un modèle Ollama."""
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False
            },
            timeout=timeout
        )
        if response.status_code == 200:
            return response.json().get("message", {}).get("content", "Pas de réponse")
        return f"Erreur Ollama: {response.status_code}"
    except Exception as e:
        return f"Erreur: {str(e)}"


def ollama_embeddings(model: str, text: str) -> str:
    """Générer des embeddings avec Ollama."""
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/embeddings",
            json={
                "model": model,
                "prompt": text
            },
            timeout=60
        )
        if response.status_code == 200:
            embeddings = response.json().get("embedding", [])
            return f"Embeddings générés: {len(embeddings)} dimensions"
        return f"Erreur Ollama: {response.status_code}"
    except Exception as e:
        return f"Erreur: {str(e)}"
