"""
RAG Apogée v2.0 - Outils ReAct
Outils de recherche sémantique pour l'AI Orchestrator
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from tools import register_tool

# Import de l'architecture RAG v2.0
try:
    from services.rag import (
        get_search_service,
        get_indexer,
        search_documents,
        SearchResponse,
        get_rag_config,
    )
    RAG_V2_AVAILABLE = True
except ImportError:
    RAG_V2_AVAILABLE = False

logger = logging.getLogger("tools.rag")


@register_tool(
    name="rag_search",
    description="Recherche sémantique dans la base de connaissances avec reranking. "
                "Utilise bge-m3 pour les embeddings et un cross-encoder pour le reranking. "
                "Retourne les documents les plus pertinents avec leurs scores.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Requête de recherche en langage naturel (FR/EN)"
            },
            "top_k": {
                "type": "integer",
                "description": "Nombre de résultats à retourner (défaut: 5)",
                "default": 5
            },
            "use_reranking": {
                "type": "boolean",
                "description": "Appliquer le reranking cross-encoder (défaut: true)",
                "default": True
            },
            "topic_filter": {
                "type": "string",
                "description": "Filtrer par topic (guide, session, documentation, code)",
                "enum": ["guide", "session", "documentation", "code", "readme", "docker", "traefik"]
            }
        },
        "required": ["query"]
    }
)
async def rag_search(
    query: str,
    top_k: int = 5,
    use_reranking: bool = True,
    topic_filter: Optional[str] = None,
    **kwargs
) -> str:
    """Recherche sémantique avec RAG Apogée v2.0"""
    
    if not RAG_V2_AVAILABLE:
        return "❌ RAG Apogée v2.0 non disponible. Vérifiez l'installation."
    
    if not query or len(query.strip()) < 3:
        return "❌ Requête trop courte (minimum 3 caractères)"
    
    try:
        search_service = get_search_service()
        response: SearchResponse = await search_service.search(
            query=query,
            top_k=top_k,
            use_reranking=use_reranking,
            topic_filter=topic_filter
        )
        
        if not response.results:
            return f"🔍 Aucun résultat trouvé pour: \"{query}\""
        
        # Formater les résultats
        lines = [
            f"🔍 **Recherche RAG**: \"{query}\"",
            f"📊 {len(response.results)} résultats (sur {response.total_found} trouvés)",
            f"⏱️ {response.search_time_ms:.0f}ms (embed: {response.embedding_time_ms:.0f}ms, rerank: {response.rerank_time_ms:.0f}ms)",
            ""
        ]
        
        for i, result in enumerate(response.results, 1):
            score_pct = int(result.score * 100)
            rerank_info = f", rerank: {int(result.rerank_score * 100)}%" if result.rerank_score else ""
            
            lines.append(f"**{i}. [{result.filename}]** ({score_pct}% pertinent{rerank_info})")
            lines.append(f"   📁 {result.source} | Topic: {result.topic}")
            lines.append(f"   Chunk {result.chunk_index + 1}/{result.total_chunks}")
            
            # Aperçu du contenu (300 chars max)
            preview = result.content[:300].replace('\n', ' ')
            if len(result.content) > 300:
                preview += "..."
            lines.append(f"   {preview}")
            lines.append("")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Erreur rag_search: {e}")
        return f"❌ Erreur recherche RAG: {e}"


@register_tool(
    name="rag_index",
    description="Indexe un nouveau document dans la base de connaissances. "
                "Le document sera découpé en chunks avec overlap et des embeddings bge-m3.",
    parameters={
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "Chemin du fichier à indexer"
            },
            "force": {
                "type": "boolean",
                "description": "Forcer la réindexation même si le fichier n'a pas changé",
                "default": False
            }
        },
        "required": ["filepath"]
    }
)
async def rag_index(
    filepath: str,
    force: bool = False,
    **kwargs
) -> str:
    """Indexe un fichier dans la base de connaissances"""
    
    if not RAG_V2_AVAILABLE:
        return "❌ RAG Apogée v2.0 non disponible."
    
    try:
        indexer = get_indexer()
        result = await indexer.index_file(filepath, force=force)
        
        if result.success:
            if result.error == "Inchangé":
                return f"📄 Fichier inchangé: {filepath} (pas de réindexation nécessaire)"
            else:
                return f"✅ Fichier indexé: {filepath}\n   {result.chunks_indexed} chunks créés"
        else:
            return f"❌ Erreur indexation: {result.error}"
            
    except Exception as e:
        logger.error(f"Erreur rag_index: {e}")
        return f"❌ Erreur indexation: {e}"


@register_tool(
    name="rag_index_directory",
    description="Indexe tous les fichiers d'un répertoire (markdown, txt). "
                "Utilise l'indexation incrémentale: seuls les fichiers modifiés sont réindexés.",
    parameters={
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "Chemin du répertoire à indexer"
            },
            "patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Patterns de fichiers (défaut: ['*.md', '*.txt'])",
                "default": ["*.md", "*.txt"]
            },
            "force": {
                "type": "boolean",
                "description": "Forcer la réindexation de tous les fichiers",
                "default": False
            }
        },
        "required": ["directory"]
    }
)
async def rag_index_directory(
    directory: str,
    patterns: List[str] = None,
    force: bool = False,
    **kwargs
) -> str:
    """Indexe un répertoire complet"""
    
    if not RAG_V2_AVAILABLE:
        return "❌ RAG Apogée v2.0 non disponible."
    
    if patterns is None:
        patterns = ["*.md", "*.txt"]
    
    try:
        indexer = get_indexer()
        stats = await indexer.index_directory(directory, patterns=patterns, force=force)
        
        return (
            f"📁 **Indexation répertoire**: {directory}\n"
            f"   Fichiers traités: {stats.total_files}\n"
            f"   Chunks indexés: {stats.total_chunks}\n"
            f"   Nouveaux: {stats.new_files} | Mis à jour: {stats.updated_files} | Inchangés: {stats.unchanged_files}\n"
            f"   Erreurs: {stats.errors}\n"
            f"   Durée: {stats.duration_ms:.0f}ms"
        )
        
    except Exception as e:
        logger.error(f"Erreur rag_index_directory: {e}")
        return f"❌ Erreur indexation répertoire: {e}"


@register_tool(
    name="rag_stats",
    description="Affiche les statistiques du système RAG: collection, embeddings, reranking, cache.",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    }
)
async def rag_stats(**kwargs) -> str:
    """Statistiques du système RAG"""
    
    if not RAG_V2_AVAILABLE:
        return "❌ RAG Apogée v2.0 non disponible."
    
    try:
        config = get_rag_config()
        search_service = get_search_service()
        indexer = get_indexer()
        
        stats = search_service.stats
        
        lines = [
            "📊 **RAG Apogée v2.0 - Statistiques**",
            "",
            "**Configuration:**",
            f"   Collection: {config.collection_name}",
            f"   Embedding: {config.embedding_model} ({config.embedding_dimensions} dim)",
            f"   Reranker: {config.reranker_model}",
            f"   Chunk size: {config.chunk_size_tokens} tokens, {config.chunk_overlap_percent*100:.0f}% overlap",
            "",
            "**Recherche:**",
            f"   Total recherches: {stats['total_searches']}",
            f"   Retrieval top_k: {config.retrieval_top_k} → Rerank top_k: {config.rerank_top_k}",
            "",
            "**Embeddings:**",
            f"   Générations: {stats['embedding']['total_generations']}",
            f"   Temps moyen: {stats['embedding']['avg_generation_time_ms']}ms",
            f"   Cache: {stats['embedding']['cache']['size']}/{stats['embedding']['cache']['max_size']}",
            f"   Hit rate: {stats['embedding']['cache']['hit_rate']}",
            "",
            "**Reranker:**",
            f"   Activé: {stats['reranker']['enabled']}",
            f"   Total reranks: {stats['reranker']['total_reranks']}",
            f"   Temps moyen: {stats['reranker']['avg_time_ms']}ms",
            "",
            "**Indexation:**",
            f"   Fichiers trackés: {indexer.tracked_files_count}",
        ]
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Erreur rag_stats: {e}")
        return f"❌ Erreur stats RAG: {e}"
