"""
RAG Apogée v2.0 - Service de Recherche Hybride
Combine recherche dense (embeddings) + BM25 + reranking
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import httpx

from .config import get_rag_config, RAGConfig
from .embeddings import get_embedding_service, EmbeddingService
from .reranker import get_reranker_service, RerankerService, RerankResult

logger = logging.getLogger("rag.search")


@dataclass
class SearchResult:
    """Résultat de recherche final"""
    content: str
    source: str
    filename: str
    topic: str
    chunk_index: int
    total_chunks: int
    score: float
    rerank_score: Optional[float] = None
    
    def to_context_string(self) -> str:
        """Formate le résultat pour injection dans le contexte"""
        return f"[{self.filename}] ({self.topic}): {self.content}"


@dataclass
class SearchResponse:
    """Réponse complète d'une recherche"""
    query: str
    results: List[SearchResult]
    total_found: int
    search_time_ms: float
    embedding_time_ms: float
    rerank_time_ms: float
    used_reranking: bool


class SearchService:
    """
    Service de recherche hybride.
    
    Pipeline:
    1. Génère l'embedding de la requête (bge-m3)
    2. Recherche dans ChromaDB (top 20)
    3. Applique le reranking (top 5)
    4. Retourne les résultats formatés
    """
    
    def __init__(
        self,
        config: Optional[RAGConfig] = None,
        embedding_service: Optional[EmbeddingService] = None,
        reranker_service: Optional[RerankerService] = None
    ):
        self.config = config or get_rag_config()
        self._embedding_service = embedding_service
        self._reranker_service = reranker_service
        self._client: Optional[httpx.AsyncClient] = None
        self._collection_id: Optional[str] = None
        self._total_searches = 0
    
    @property
    def embedding_service(self) -> EmbeddingService:
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service
    
    @property
    def reranker_service(self) -> RerankerService:
        if self._reranker_service is None:
            self._reranker_service = get_reranker_service()
        return self._reranker_service
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy initialization du client HTTP"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.config.search_timeout)
        return self._client
    
    async def _get_collection_id(self) -> Optional[str]:
        """Récupère l'ID de la collection ChromaDB"""
        if self._collection_id:
            return self._collection_id
        
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.config.chromadb_url}/api/v2/tenants/default_tenant/databases/default_database/collections"
            )
            
            if response.status_code == 200:
                for col in response.json():
                    if col.get("name") == self.config.collection_name:
                        self._collection_id = col.get("id")
                        return self._collection_id
                        
        except Exception as e:
            logger.error(f"Erreur récupération collection ID: {e}")
        
        return None
    
    async def _search_chromadb(
        self,
        query_embedding: List[float],
        n_results: int = 20
    ) -> List[Tuple[str, Dict, float]]:
        """
        Recherche dans ChromaDB par similarité vectorielle.
        
        Returns:
            Liste de (content, metadata, distance)
        """
        collection_id = await self._get_collection_id()
        if not collection_id:
            logger.error(f"Collection '{self.config.collection_name}' non trouvée")
            return []
        
        try:
            client = await self._get_client()
            
            response = await client.post(
                f"{self.config.chromadb_url}/api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}/query",
                json={
                    "query_embeddings": [query_embedding],
                    "n_results": n_results,
                    "include": ["documents", "metadatas", "distances"]
                }
            )
            
            if response.status_code != 200:
                logger.error(f"ChromaDB search error: {response.status_code}")
                return []
            
            data = response.json()
            documents = data.get("documents", [[]])[0]
            metadatas = data.get("metadatas", [[]])[0]
            distances = data.get("distances", [[]])[0]
            
            results = []
            for doc, meta, dist in zip(documents, metadatas, distances):
                results.append((doc, meta, dist))
            
            return results
            
        except Exception as e:
            logger.error(f"Erreur recherche ChromaDB: {e}")
            return []
    
    def _preprocess_query(self, query: str) -> str:
        """Prétraitement de la requête"""
        # Normaliser les espaces
        query = re.sub(r'\s+', ' ', query.strip())
        # Limiter la longueur
        return query[:1000]
    
    async def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        use_reranking: bool = True,
        topic_filter: Optional[str] = None
    ) -> SearchResponse:
        """
        Effectue une recherche hybride.
        
        Args:
            query: Requête en langage naturel
            top_k: Nombre de résultats (défaut: config.default_top_k)
            use_reranking: Appliquer le reranking (défaut: True)
            topic_filter: Filtrer par topic (optionnel)
            
        Returns:
            SearchResponse avec les résultats
        """
        if top_k is None:
            top_k = self.config.default_top_k
        
        start_time = datetime.now()
        query = self._preprocess_query(query)
        
        if not query:
            return SearchResponse(
                query=query,
                results=[],
                total_found=0,
                search_time_ms=0,
                embedding_time_ms=0,
                rerank_time_ms=0,
                used_reranking=False
            )
        
        # 1. Générer l'embedding de la requête
        embed_start = datetime.now()
        embed_result = await self.embedding_service.generate(query)
        embedding_time_ms = (datetime.now() - embed_start).total_seconds() * 1000
        
        if not embed_result:
            logger.error("Impossible de générer l'embedding de la requête")
            return SearchResponse(
                query=query,
                results=[],
                total_found=0,
                search_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                embedding_time_ms=embedding_time_ms,
                rerank_time_ms=0,
                used_reranking=False
            )
        
        # 2. Recherche dans ChromaDB
        retrieval_count = self.config.retrieval_top_k if use_reranking else top_k
        raw_results = await self._search_chromadb(embed_result.embedding, retrieval_count)
        
        # Filtrer par topic si spécifié
        if topic_filter:
            raw_results = [
                (doc, meta, dist) for doc, meta, dist in raw_results
                if meta.get("topic", "").lower() == topic_filter.lower()
            ]
        
        if not raw_results:
            return SearchResponse(
                query=query,
                results=[],
                total_found=0,
                search_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                embedding_time_ms=embedding_time_ms,
                rerank_time_ms=0,
                used_reranking=False
            )
        
        # 3. Reranking
        rerank_time_ms = 0
        if use_reranking and len(raw_results) > top_k:
            rerank_start = datetime.now()
            reranked, rerank_stats = await self.reranker_service.rerank(
                query, raw_results, top_k
            )
            rerank_time_ms = (datetime.now() - rerank_start).total_seconds() * 1000
            
            # Convertir en SearchResult
            final_results = []
            for r in reranked:
                final_results.append(SearchResult(
                    content=r.content,
                    source=r.metadata.get("source", "unknown"),
                    filename=r.metadata.get("filename", "unknown"),
                    topic=r.metadata.get("topic", "general"),
                    chunk_index=r.metadata.get("chunk_index", 0),
                    total_chunks=r.metadata.get("total_chunks", 1),
                    score=r.combined_score,
                    rerank_score=r.rerank_score
                ))
        else:
            # Sans reranking, convertir directement
            final_results = []
            for doc, meta, dist in raw_results[:top_k]:
                similarity = 1.0 / (1.0 + dist)
                final_results.append(SearchResult(
                    content=doc,
                    source=meta.get("source", "unknown"),
                    filename=meta.get("filename", "unknown"),
                    topic=meta.get("topic", "general"),
                    chunk_index=meta.get("chunk_index", 0),
                    total_chunks=meta.get("total_chunks", 1),
                    score=similarity,
                    rerank_score=None
                ))
        
        self._total_searches += 1
        total_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return SearchResponse(
            query=query,
            results=final_results,
            total_found=len(raw_results),
            search_time_ms=total_time_ms,
            embedding_time_ms=embedding_time_ms,
            rerank_time_ms=rerank_time_ms,
            used_reranking=use_reranking and len(raw_results) > top_k
        )
    
    async def get_context_for_query(
        self,
        query: str,
        max_chars: Optional[int] = None
    ) -> Optional[str]:
        """
        Obtient le contexte pertinent pour une requête.
        
        Utilisé pour l'injection automatique dans les prompts.
        
        Args:
            query: Requête utilisateur
            max_chars: Limite de caractères (défaut: config.context_max_chars)
            
        Returns:
            Contexte formaté ou None si rien de pertinent
        """
        if max_chars is None:
            max_chars = self.config.context_max_chars
        
        response = await self.search(query, top_k=5, use_reranking=True)
        
        if not response.results:
            return None
        
        # Filtrer par score minimum
        relevant = [
            r for r in response.results
            if r.score >= self.config.context_min_score
        ]
        
        if not relevant:
            return None
        
        # Construire le contexte
        context_parts = []
        current_length = 0
        
        for result in relevant:
            entry = result.to_context_string()
            if current_length + len(entry) > max_chars:
                break
            context_parts.append(entry)
            current_length += len(entry) + 2  # +2 pour \n\n
        
        if not context_parts:
            return None
        
        return "\n\n".join(context_parts)
    
    @property
    def stats(self) -> Dict:
        """Statistiques du service"""
        return {
            "total_searches": self._total_searches,
            "collection": self.config.collection_name,
            "embedding": self.embedding_service.stats,
            "reranker": self.reranker_service.stats
        }
    
    async def close(self):
        """Ferme les ressources"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton
_search_service: Optional[SearchService] = None


def get_search_service() -> SearchService:
    """Obtient l'instance singleton du service de recherche"""
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service


async def search_documents(
    query: str,
    top_k: int = 5,
    use_reranking: bool = True
) -> SearchResponse:
    """
    Fonction utilitaire pour rechercher des documents.
    
    Args:
        query: Requête de recherche
        top_k: Nombre de résultats
        use_reranking: Utiliser le reranking
        
    Returns:
        SearchResponse
    """
    service = get_search_service()
    return await service.search(query, top_k, use_reranking)
