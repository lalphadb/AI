"""
Outils de mémoire sémantique pour AI Orchestrator v5.0
Intégration ChromaDB avec embeddings Ollama (bge-m3)

- memory_store: Stocker une information en mémoire
- memory_recall: Rappeler des informations par recherche sémantique
- memory_list: Lister les souvenirs
- memory_delete: Supprimer un souvenir
"""

import logging
import os
from datetime import datetime

import httpx

from tools import register_tool

logger = logging.getLogger(__name__)

# Configuration
CHROMADB_HOST = os.getenv("CHROMADB_HOST", "chromadb")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8000"))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://10.10.10.46:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")
MEMORY_COLLECTION = "ai_orchestrator_memory_v3"

# Clients (lazy loading)
_chroma_client = None
_memory_collection = None


async def get_embedding(text: str) -> list[float] | None:
    """Obtenir embedding via Ollama (bge-m3 - 1024 dim)"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/embeddings", json={"model": EMBEDDING_MODEL, "prompt": text}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("embedding")
            else:
                logger.error(f"Ollama embedding error: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return None


def get_chroma_client():
    """Obtenir le client ChromaDB (singleton)"""
    global _chroma_client
    if _chroma_client is None:
        try:
            import chromadb

            _chroma_client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
            logger.info(f"ChromaDB connecte: {CHROMADB_HOST}:{CHROMADB_PORT}")
        except Exception as e:
            logger.error(f"ChromaDB non disponible: {e}")
            return None
    return _chroma_client


def get_memory_collection():
    """Obtenir ou creer la collection memoire v2"""
    global _memory_collection
    if _memory_collection is None:
        client = get_chroma_client()
        if client:
            try:
                _memory_collection = client.get_or_create_collection(
                    name=MEMORY_COLLECTION,
                    metadata={
                        "description": "Memoire semantique AI Orchestrator v2 - Ollama embeddings",
                        "embedding_model": EMBEDDING_MODEL,
                        "embedding_dim": "1024",
                    },
                )
                logger.info(f"Collection memoire v2: {MEMORY_COLLECTION}")
            except Exception as e:
                logger.error(f"Erreur collection: {e}")
                return None
    return _memory_collection


@register_tool("memory_store")
async def memory_store(params: dict) -> str:
    """
    Stocker une information en memoire semantique avec embeddings Ollama.

    Args:
        key: Cle/identifiant unique
        value: Contenu a memoriser
        category: Categorie (optionnel: user, system, project, fact, infra)
    """
    key = params.get("key", "")
    value = params.get("value", "")
    category = params.get("category", "general")

    if not key or not value:
        return "Erreur: key et value requis pour memory_store"

    collection = get_memory_collection()
    if not collection:
        return "Memoire non disponible (ChromaDB deconnecte)"

    try:
        embedding = await get_embedding(f"{category}: {key} - {value}")
        if not embedding:
            return "Impossible de generer l'embedding (Ollama indisponible)"

        doc_id = f"{category}_{key}".replace(" ", "_").lower()[:64]

        metadata = {
            "key": key[:100],
            "category": category,
            "timestamp": datetime.now().isoformat(),
            "source": "ai_orchestrator",
            "embedding_model": EMBEDDING_MODEL,
        }

        collection.upsert(
            ids=[doc_id], documents=[value], embeddings=[embedding], metadatas=[metadata]
        )

        logger.info(f"Memorise: {key} ({category}) avec {EMBEDDING_MODEL}")
        return f"Memorise: '{key}' dans categorie '{category}' (embedding: {EMBEDDING_MODEL})"

    except Exception as e:
        logger.error(f"Erreur memory_store: {e}")
        return f"Erreur stockage memoire: {str(e)}"


@register_tool("memory_recall")
async def memory_recall(params: dict) -> str:
    """
    Rappeler des informations par recherche semantique avec embeddings Ollama.

    Args:
        query: Terme ou concept a rechercher
        limit: Nombre max de resultats (defaut: 5)
        category: Filtrer par categorie (optionnel)
    """
    query = params.get("query", "")
    limit = params.get("limit", 5)
    category = params.get("category", None)

    if not query:
        return "Erreur: query requis pour memory_recall"

    collection = get_memory_collection()
    if not collection:
        return "Memoire non disponible (ChromaDB deconnecte)"

    try:
        try:
            limit = min(int(limit), 20)
        except (ValueError, TypeError):
            limit = 5

        query_embedding = await get_embedding(query)
        if not query_embedding:
            return "Impossible de generer l'embedding pour la recherche"

        where_filter = None
        if category:
            where_filter = {"category": category}

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        if not results or not results.get("documents") or not results["documents"][0]:
            return f"Aucun souvenir trouve pour: '{query}'"

        output_lines = [f"Souvenirs pour '{query}':"]

        documents = results["documents"][0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, (doc, meta, dist) in enumerate(
            zip(documents, metadatas, distances, strict=False), 1
        ):
            key = meta.get("key", "inconnu")
            cat = meta.get("category", "?")
            timestamp = meta.get("timestamp", "")[:10]

            similarity = max(0, 100 - (dist * 10))
            relevance = f"{similarity:.0f}%"

            output_lines.append(f"\n{i}. [{cat}] {key} (pertinence: {relevance})")
            output_lines.append(f"   -> {doc[:300]}{'...' if len(doc) > 300 else ''}")
            if timestamp:
                output_lines.append(f"   Date: {timestamp}")

        logger.info(f"Rappel: {query} -> {len(documents)} resultats")
        return "\n".join(output_lines)

    except Exception as e:
        logger.error(f"Erreur memory_recall: {e}")
        return f"Erreur rappel memoire: {str(e)}"


@register_tool("memory_list")
async def memory_list(params: dict) -> str:
    """Lister tous les souvenirs stockes"""
    category = params.get("category", None)
    limit = params.get("limit", 20)

    collection = get_memory_collection()
    if not collection:
        return "Memoire non disponible"

    try:
        where_filter = {"category": category} if category else None

        results = collection.get(
            where=where_filter, limit=min(int(limit), 100), include=["documents", "metadatas"]
        )

        if not results or not results.get("ids"):
            return "Memoire vide (collection v2)"

        output_lines = [f"Souvenirs stockes ({len(results['ids'])}):"]

        for i, (doc_id, doc, meta) in enumerate(
            zip(results["ids"], results["documents"], results["metadatas"], strict=False), 1
        ):
            key = meta.get("key", doc_id)
            cat = meta.get("category", "?")
            output_lines.append(f"{i}. [{cat}] {key}: {doc[:100]}...")

        return "\n".join(output_lines)

    except Exception as e:
        return f"Erreur: {str(e)}"


@register_tool("memory_delete")
async def memory_delete(params: dict) -> str:
    """Supprimer un souvenir par cle"""
    key = params.get("key", "")
    category = params.get("category", "general")

    if not key:
        return "Erreur: key requis"

    collection = get_memory_collection()
    if not collection:
        return "Memoire non disponible"

    try:
        doc_id = f"{category}_{key}".replace(" ", "_").lower()[:64]
        collection.delete(ids=[doc_id])
        return f"Souvenir supprime: {key}"
    except Exception as e:
        return f"Erreur: {str(e)}"


@register_tool("memory_stats")
async def memory_stats(params: dict) -> str:
    """Obtenir les statistiques de la memoire"""
    collection = get_memory_collection()
    if not collection:
        return "Memoire non disponible"

    try:
        count = collection.count()

        results = collection.get(limit=1000, include=["metadatas"])

        categories = {}
        for meta in results.get("metadatas", []):
            cat = meta.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

        output = [
            "Statistiques memoire v2:",
            f"- Collection: {MEMORY_COLLECTION}",
            f"- Embedding: {EMBEDDING_MODEL} (1024 dim)",
            f"- Total documents: {count}",
            "- Par categorie:",
        ]

        for cat, cnt in sorted(categories.items(), key=lambda x: -x[1]):
            output.append(f"  - {cat}: {cnt}")

        return "\n".join(output)

    except Exception as e:
        return f"Erreur: {str(e)}"
