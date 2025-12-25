"""
Outils de mémoire sémantique pour AI Orchestrator v4.0
Intégration ChromaDB pour la persistance des connaissances

- memory_store: Stocker une information en mémoire
- memory_recall: Rappeler des informations par recherche sémantique
"""

import os
import logging
from datetime import datetime
from typing import Optional

from tools import register_tool

logger = logging.getLogger(__name__)

# Configuration ChromaDB
CHROMADB_HOST = os.getenv("CHROMADB_HOST", "chromadb")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8000"))
MEMORY_COLLECTION = "ai_orchestrator_memory"

# Client ChromaDB (lazy loading)
_chroma_client = None
_memory_collection = None


def get_chroma_client():
    """Obtenir le client ChromaDB (singleton)"""
    global _chroma_client
    if _chroma_client is None:
        try:
            import chromadb
            _chroma_client = chromadb.HttpClient(
                host=CHROMADB_HOST,
                port=CHROMADB_PORT
            )
            logger.info(f"✅ ChromaDB connecté: {CHROMADB_HOST}:{CHROMADB_PORT}")
        except Exception as e:
            logger.error(f"❌ ChromaDB non disponible: {e}")
            return None
    return _chroma_client


def get_memory_collection():
    """Obtenir ou créer la collection mémoire"""
    global _memory_collection
    if _memory_collection is None:
        client = get_chroma_client()
        if client:
            try:
                _memory_collection = client.get_or_create_collection(
                    name=MEMORY_COLLECTION,
                    metadata={"description": "Mémoire sémantique AI Orchestrator"}
                )
                logger.info(f"✅ Collection mémoire: {MEMORY_COLLECTION}")
            except Exception as e:
                logger.error(f"❌ Erreur collection: {e}")
                return None
    return _memory_collection


@register_tool("memory_store")
async def memory_store(params: dict) -> str:
    """
    Stocker une information en mémoire sémantique.
    
    Args:
        key: Clé/identifiant unique
        value: Contenu à mémoriser
        category: Catégorie (optionnel: user, system, project, fact)
    """
    key = params.get("key", "")
    value = params.get("value", "")
    category = params.get("category", "general")
    
    if not key or not value:
        return "Erreur: key et value requis pour memory_store"
    
    collection = get_memory_collection()
    if not collection:
        return "⚠️ Mémoire non disponible (ChromaDB déconnecté)"
    
    try:
        # Générer un ID unique basé sur la clé
        doc_id = f"{category}_{key}".replace(" ", "_").lower()
        
        # Métadonnées enrichies
        metadata = {
            "key": key,
            "category": category,
            "timestamp": datetime.now().isoformat(),
            "source": "ai_orchestrator"
        }
        
        # Upsert (ajouter ou mettre à jour)
        collection.upsert(
            ids=[doc_id],
            documents=[value],
            metadatas=[metadata]
        )
        
        logger.info(f"🧠 Mémorisé: {key} ({category})")
        return f"✅ Mémorisé: '{key}' dans catégorie '{category}'"
        
    except Exception as e:
        logger.error(f"Erreur memory_store: {e}")
        return f"❌ Erreur stockage mémoire: {str(e)}"


@register_tool("memory_recall")
async def memory_recall(params: dict) -> str:
    """
    Rappeler des informations par recherche sémantique.
    
    Args:
        query: Terme ou concept à rechercher
        limit: Nombre max de résultats (défaut: 5)
        category: Filtrer par catégorie (optionnel)
    """
    query = params.get("query", "")
    limit = params.get("limit", 5)
    category = params.get("category", None)
    
    if not query:
        return "Erreur: query requis pour memory_recall"
    
    collection = get_memory_collection()
    if not collection:
        return "⚠️ Mémoire non disponible (ChromaDB déconnecté)"
    
    try:
        # Validation du limit
        try:
            limit = min(int(limit), 20)
        except (ValueError, TypeError):
            limit = 5
        
        # Préparer le filtre
        where_filter = None
        if category:
            where_filter = {"category": category}
        
        # Recherche sémantique
        results = collection.query(
            query_texts=[query],
            n_results=limit,
            where=where_filter
        )
        
        # Formater les résultats
        if not results or not results.get('documents') or not results['documents'][0]:
            return f"🔍 Aucun souvenir trouvé pour: '{query}'"
        
        output_lines = [f"🧠 Souvenirs pour '{query}':"]
        
        documents = results['documents'][0]
        metadatas = results.get('metadatas', [[]])[0]
        distances = results.get('distances', [[]])[0]
        
        for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances), 1):
            key = meta.get('key', 'inconnu')
            cat = meta.get('category', '?')
            timestamp = meta.get('timestamp', '')[:10]  # Date seulement
            relevance = f"{(1-dist)*100:.0f}%" if dist < 1 else "?"
            
            output_lines.append(f"\n{i}. [{cat}] {key} (pertinence: {relevance})")
            output_lines.append(f"   → {doc[:200]}{'...' if len(doc) > 200 else ''}")
            if timestamp:
                output_lines.append(f"   📅 {timestamp}")
        
        logger.info(f"🔍 Rappel: {query} → {len(documents)} résultats")
        return "\n".join(output_lines)
        
    except Exception as e:
        logger.error(f"Erreur memory_recall: {e}")
        return f"❌ Erreur rappel mémoire: {str(e)}"


@register_tool("memory_list")
async def memory_list(params: dict) -> str:
    """Lister tous les souvenirs stockés"""
    category = params.get("category", None)
    limit = params.get("limit", 20)
    
    collection = get_memory_collection()
    if not collection:
        return "⚠️ Mémoire non disponible"
    
    try:
        # Récupérer tous les documents
        where_filter = {"category": category} if category else None
        
        results = collection.get(
            where=where_filter,
            limit=min(int(limit), 100)
        )
        
        if not results or not results.get('ids'):
            return "🧠 Mémoire vide"
        
        output_lines = [f"🧠 Souvenirs stockés ({len(results['ids'])}):\n"]
        
        for i, (doc_id, doc, meta) in enumerate(
            zip(results['ids'], results['documents'], results['metadatas']), 1
        ):
            key = meta.get('key', doc_id)
            cat = meta.get('category', '?')
            output_lines.append(f"{i}. [{cat}] {key}: {doc[:100]}...")
        
        return "\n".join(output_lines)
        
    except Exception as e:
        return f"❌ Erreur: {str(e)}"


@register_tool("memory_delete")
async def memory_delete(params: dict) -> str:
    """Supprimer un souvenir par clé"""
    key = params.get("key", "")
    category = params.get("category", "general")
    
    if not key:
        return "Erreur: key requis"
    
    collection = get_memory_collection()
    if not collection:
        return "⚠️ Mémoire non disponible"
    
    try:
        doc_id = f"{category}_{key}".replace(" ", "_").lower()
        collection.delete(ids=[doc_id])
        return f"✅ Souvenir supprimé: {key}"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"
