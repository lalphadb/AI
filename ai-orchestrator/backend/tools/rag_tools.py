"""
Outils RAG Apogée pour AI Orchestrator
Recherche sémantique multilingue avec bge-m3

- rag_search: Recherche dans la base de connaissances
- rag_index: Indexer un nouveau document
- rag_stats: Statistiques de l'index RAG

Note: Le reranker bge-reranker-v2-m3 sera intégré via sentence-transformers
dans une prochaine version (Phase 3).
"""

import logging
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

import httpx

from tools import register_tool

logger = logging.getLogger(__name__)

# Configuration RAG Apogée
CHROMADB_HOST = os.getenv("CHROMADB_HOST", "chromadb")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8000"))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://10.10.10.46:11434")

# Modèles RAG
EMBEDDING_MODEL = "bge-m3"  # Multilingue FR/EN, 1024 dim, 8K contexte
COLLECTION_NAME = "ai_orchestrator_memory_v3"

# Cache embeddings
_embedding_cache: Dict[int, List[float]] = {}


async def get_embedding_bge(text: str) -> Optional[List[float]]:
    """Obtenir embedding via bge-m3 (multilingue, 1024 dim)"""
    cache_key = hash(text[:500])
    if cache_key in _embedding_cache:
        return _embedding_cache[cache_key]
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": EMBEDDING_MODEL, "prompt": text}
            )
            if response.status_code == 200:
                embedding = response.json().get("embedding", [])
                if embedding:
                    _embedding_cache[cache_key] = embedding
                    return embedding
    except Exception as e:
        logger.error(f"Erreur embedding bge-m3: {e}")
    return None


async def get_collection_id() -> Optional[str]:
    """Récupérer l'UUID de la collection v3"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"http://{CHROMADB_HOST}:{CHROMADB_PORT}/api/v2/tenants/default_tenant/databases/default_database/collections"
            )
            if r.status_code == 200:
                for col in r.json():
                    if col.get("name") == COLLECTION_NAME:
                        return col.get("id")
    except Exception as e:
        logger.error(f"Erreur récupération collection ID: {e}")
    return None


@register_tool(
    "rag_search",
    description="Recherche sémantique dans la base de connaissances (français/anglais). Utilise bge-m3 multilingue.",
    parameters={"query": "str", "top_k": "int (optionnel, défaut 5)"}
)
async def rag_search(params: dict) -> str:
    """Recherche RAG avec bge-m3"""
    query = params.get("query", "")
    top_k = int(params.get("top_k", 5))
    
    if not query:
        return "❌ Erreur: query requis"
    
    # Obtenir l'embedding de la requête
    query_embedding = await get_embedding_bge(query)
    if not query_embedding:
        return "❌ Erreur: impossible de générer l'embedding"
    
    # Récupérer l'ID de la collection
    collection_id = await get_collection_id()
    if not collection_id:
        return "❌ Erreur: collection RAG non trouvée"
    
    # Recherche dans ChromaDB
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"http://{CHROMADB_HOST}:{CHROMADB_PORT}/api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}/query",
                json={
                    "query_embeddings": [query_embedding],
                    "n_results": top_k,
                    "include": ["documents", "metadatas", "distances"]
                }
            )
            
            if r.status_code != 200:
                return f"❌ Erreur ChromaDB: {r.status_code}"
            
            data = r.json()
            docs = data.get("documents", [[]])[0]
            metas = data.get("metadatas", [[]])[0]
            dists = data.get("distances", [[]])[0]
            
            if not docs:
                return "📭 Aucun résultat trouvé pour cette recherche."
            
            # Formater la réponse (distance L2: plus petit = plus similaire)
            result = [f"🔍 **Recherche RAG:** \"{query}\"", f"📚 **{len(docs)} résultats:**\n"]
            
            for i, (doc, meta, dist) in enumerate(zip(docs, metas, dists), 1):
                source = meta.get("source", "inconnu")
                topic = meta.get("topic", "")
                # Normaliser le score (inversement proportionnel à la distance)
                score = max(0, 1 - (dist / 1000))  # Normalisation approximative
                content = doc[:300] + "..." if len(doc) > 300 else doc
                
                result.append(f"**{i}. [{source}]** (pertinence: {score:.1%})")
                if topic:
                    result.append(f"   📁 Topic: {topic}")
                result.append(f"   {content}\n")
            
            return "\n".join(result)
            
    except Exception as e:
        logger.error(f"Erreur recherche RAG: {e}")
        return f"❌ Erreur recherche: {str(e)}"


@register_tool(
    "rag_index",
    description="Indexer un nouveau document dans la base de connaissances",
    parameters={"content": "str", "source": "str", "topic": "str (optionnel)"}
)
async def rag_index(params: dict) -> str:
    """Indexer un document dans ChromaDB avec bge-m3"""
    content = params.get("content", "")
    source = params.get("source", "user")
    topic = params.get("topic", "general")
    
    if not content:
        return "❌ Erreur: content requis"
    
    if len(content) < 10:
        return "❌ Erreur: contenu trop court (min 10 caractères)"
    
    # Générer l'embedding
    embedding = await get_embedding_bge(content)
    if not embedding:
        return "❌ Erreur: impossible de générer l'embedding"
    
    # Récupérer l'ID de la collection
    collection_id = await get_collection_id()
    if not collection_id:
        return "❌ Erreur: collection RAG non trouvée"
    
    # Créer l'ID du document
    doc_id = f"doc_{hash(content[:100])}_{len(content)}"
    
    # Métadonnées
    metadata = {
        "source": source,
        "topic": topic,
        "lang": "fr",
        "indexed_at": datetime.now().isoformat(),
        "content_length": len(content)
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"http://{CHROMADB_HOST}:{CHROMADB_PORT}/api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}/add",
                json={
                    "ids": [doc_id],
                    "documents": [content],
                    "embeddings": [embedding],
                    "metadatas": [metadata]
                }
            )
            
            if r.status_code in (200, 201):
                return f"✅ Document indexé avec succès!\n- ID: {doc_id}\n- Source: {source}\n- Topic: {topic}\n- Taille: {len(content)} caractères"
            else:
                return f"❌ Erreur indexation: {r.status_code} - {r.text[:200]}"
                
    except Exception as e:
        logger.error(f"Erreur indexation: {e}")
        return f"❌ Erreur: {str(e)}"


@register_tool(
    "rag_stats",
    description="Affiche les statistiques de la base de connaissances RAG"
)
async def rag_stats(params: dict) -> str:
    """Statistiques de l'index RAG"""
    collection_id = await get_collection_id()
    
    if not collection_id:
        return "❌ Collection RAG non trouvée"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Récupérer les infos de la collection
            r = await client.get(
                f"http://{CHROMADB_HOST}:{CHROMADB_PORT}/api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}"
            )
            
            if r.status_code != 200:
                return f"❌ Erreur: {r.status_code}"
            
            col_info = r.json()
            
            # Compter les documents
            r2 = await client.get(
                f"http://{CHROMADB_HOST}:{CHROMADB_PORT}/api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}/count"
            )
            
            count = r2.json() if r2.status_code == 200 else "?"
            
            result = [
                "📊 **Statistiques RAG Apogée**\n",
                f"- **Collection:** {COLLECTION_NAME}",
                f"- **ID:** {collection_id[:8]}...",
                f"- **Documents:** {count}",
                f"- **Embedding:** {EMBEDDING_MODEL} (1024 dim, multilingue)",
                f"- **Cache:** {len(_embedding_cache)} embeddings en cache",
            ]
            
            metadata = col_info.get("metadata", {})
            if metadata:
                result.append(f"- **Description:** {metadata.get('description', 'N/A')}")
            
            return "\n".join(result)
            
    except Exception as e:
        return f"❌ Erreur: {str(e)}"


def clear_embedding_cache():
    """Vider le cache d'embeddings"""
    global _embedding_cache
    _embedding_cache = {}
