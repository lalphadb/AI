#!/usr/bin/env python3
"""
Service RAG Apogée pour AI Orchestrator
Architecture: bge-m3 (embedding) + bge-reranker-v2-m3 (rerank) + Qwen3 (génération)

Pipeline:
1. Query → bge-m3 embedding
2. ChromaDB recherche hybride (dense + metadata)
3. Reranker filtre top-k
4. Context enrichi → LLM

Optimisé pour le français.
"""

import asyncio
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import httpx
import chromadb
from chromadb.config import Settings

# Import du reranker
from services.reranker import rerank_documents, hybrid_search_with_rerank

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://10.10.10.46:11434")
CHROMADB_HOST = os.getenv("CHROMADB_HOST", "chromadb")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8000"))

EMBEDDING_MODEL = "bge-m3"
COLLECTION_NAME = "ai_orchestrator_memory_v3"

# Paramètres RAG
DEFAULT_TOP_K = 20  # Résultats initiaux
RERANK_TOP_K = 5    # Après reranking
MIN_RELEVANCE_SCORE = 0.3


@dataclass
class RAGResult:
    """Résultat d'une recherche RAG"""
    query: str
    documents: List[Dict]
    context: str
    sources: List[str]
    scores: List[float]


class RAGService:
    """Service RAG avec recherche hybride et reranking"""
    
    def __init__(self):
        self.chroma_client = None
        self.collection = None
        self._embedding_cache: Dict[str, List[float]] = {}
    
    def _get_collection(self):
        """Obtenir la collection ChromaDB"""
        if self.chroma_client is None:
            self.chroma_client = chromadb.HttpClient(
                host=CHROMADB_HOST,
                port=CHROMADB_PORT,
                settings=Settings(anonymized_telemetry=False)
            )
        
        if self.collection is None:
            self.collection = self.chroma_client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={
                    "description": "Mémoire sémantique v3 - bge-m3 multilingue FR/EN",
                    "embedding_model": EMBEDDING_MODEL,
                    "hnsw:space": "cosine"
                }
            )
        
        return self.collection
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Obtenir l'embedding d'un texte via bge-m3"""
        # Cache
        cache_key = hash(text[:500])
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                response = await client.post(
                    f"{OLLAMA_URL}/api/embeddings",
                    json={"model": EMBEDDING_MODEL, "prompt": text}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    embedding = data.get("embedding", [])
                    if embedding:
                        self._embedding_cache[cache_key] = embedding
                        return embedding
        except Exception as e:
            print(f"⚠️ Erreur embedding bge-m3: {e}")
        
        return None
    
    async def search(
        self,
        query: str,
        top_k: int = RERANK_TOP_K,
        use_reranker: bool = True,
        filters: Optional[Dict] = None
    ) -> RAGResult:
        """
        Recherche RAG complète avec reranking optionnel.
        
        Args:
            query: Requête en français ou anglais
            top_k: Nombre de résultats finaux
            use_reranker: Utiliser le reranker pour filtrer
            filters: Filtres metadata ChromaDB
            
        Returns:
            RAGResult avec documents et contexte
        """
        collection = self._get_collection()
        
        # 1. Obtenir l'embedding de la query
        query_embedding = await self.get_embedding(query)
        if not query_embedding:
            return RAGResult(
                query=query,
                documents=[],
                context="",
                sources=[],
                scores=[]
            )
        
        # 2. Recherche dense dans ChromaDB
        search_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": DEFAULT_TOP_K if use_reranker else top_k,
            "include": ["documents", "metadatas", "distances"]
        }
        
        if filters:
            search_kwargs["where"] = filters
        
        results = collection.query(**search_kwargs)
        
        # Formater les résultats
        documents = []
        if results and results.get("documents") and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                distance = results["distances"][0][i] if results.get("distances") else 1.0
                
                # Convertir distance en score (cosine: 0 = identique, 2 = opposé)
                score = 1 - (distance / 2)
                
                documents.append({
                    "content": doc,
                    "metadata": metadata,
                    "score": score,
                    "source": metadata.get("source", "unknown")
                })
        
        # 3. Reranking si activé
        if use_reranker and documents:
            documents = await rerank_documents(
                query=query,
                documents=documents,
                top_k=top_k,
                score_threshold=MIN_RELEVANCE_SCORE
            )
        else:
            documents = documents[:top_k]
        
        # 4. Construire le contexte
        context_parts = []
        sources = []
        scores = []
        
        for doc in documents:
            content = doc.get("content", "")
            source = doc.get("source", "unknown")
            score = doc.get("rerank_score", doc.get("score", 0))
            
            context_parts.append(f"[Source: {source}]\n{content}")
            sources.append(source)
            scores.append(score)
        
        context = "\n\n---\n\n".join(context_parts)
        
        return RAGResult(
            query=query,
            documents=documents,
            context=context,
            sources=sources,
            scores=scores
        )
    
    async def add_document(
        self,
        content: str,
        metadata: Optional[Dict] = None,
        doc_id: Optional[str] = None
    ) -> bool:
        """Ajouter un document à l'index"""
        collection = self._get_collection()
        
        embedding = await self.get_embedding(content)
        if not embedding:
            return False
        
        if doc_id is None:
            doc_id = f"doc_{hash(content[:100])}_{len(content)}"
        
        if metadata is None:
            metadata = {}
        
        metadata["indexed_at"] = asyncio.get_event_loop().time()
        metadata["content_length"] = len(content)
        
        try:
            collection.upsert(
                ids=[doc_id],
                documents=[content],
                embeddings=[embedding],
                metadatas=[metadata]
            )
            return True
        except Exception as e:
            print(f"⚠️ Erreur ajout document: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Obtenir les statistiques de l'index"""
        collection = self._get_collection()
        
        return {
            "collection_name": COLLECTION_NAME,
            "embedding_model": EMBEDDING_MODEL,
            "document_count": collection.count(),
            "cache_size": len(self._embedding_cache)
        }
    
    def clear_cache(self):
        """Vider le cache d'embeddings"""
        self._embedding_cache = {}


# Instance singleton
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Obtenir l'instance RAG singleton"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


# Test standalone
if __name__ == "__main__":
    async def test():
        rag = get_rag_service()
        
        # Test stats
        stats = await rag.get_stats()
        print(f"📊 Stats RAG: {stats}")
        
        # Test recherche
        result = await rag.search("Comment configurer Docker?", top_k=3)
        print(f"\n🔍 Recherche: {result.query}")
        print(f"📄 Documents trouvés: {len(result.documents)}")
        for i, doc in enumerate(result.documents, 1):
            print(f"  {i}. Score: {result.scores[i-1]:.3f} - {doc['content'][:100]}...")
    
    asyncio.run(test())
