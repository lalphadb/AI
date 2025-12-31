"""
RAG Apogée v2.0 - Service d'Embeddings
Génération d'embeddings via Ollama avec cache LRU
"""

import asyncio
import hashlib
import logging
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import httpx

from .config import get_rag_config, RAGConfig

logger = logging.getLogger("rag.embeddings")


@dataclass
class EmbeddingResult:
    """Résultat d'une génération d'embedding"""
    embedding: List[float]
    model: str
    cached: bool
    generation_time_ms: float


class LRUCache:
    """Cache LRU thread-safe pour les embeddings"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: OrderedDict[int, List[float]] = OrderedDict()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: int) -> Optional[List[float]]:
        """Récupère un embedding du cache"""
        if key in self._cache:
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        return None
    
    def put(self, key: int, value: List[float]):
        """Ajoute un embedding au cache"""
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            self._cache[key] = value
    
    def clear(self):
        """Vide le cache"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
    
    @property
    def stats(self) -> Dict:
        """Statistiques du cache"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%"
        }


class EmbeddingService:
    """Service de génération d'embeddings avec cache"""
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or get_rag_config()
        self._cache = LRUCache(max_size=self.config.embedding_cache_size)
        self._client: Optional[httpx.AsyncClient] = None
        self._total_generations = 0
        self._total_time_ms = 0.0
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy initialization du client HTTP"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.config.embedding_timeout)
        return self._client
    
    def _compute_cache_key(self, text: str) -> int:
        """Calcule la clé de cache pour un texte"""
        # Utilise les 500 premiers caractères pour la clé
        normalized = text[:500].lower().strip()
        return hash(normalized)
    
    async def generate(self, text: str, use_cache: bool = True) -> Optional[EmbeddingResult]:
        """
        Génère un embedding pour le texte donné.
        
        Args:
            text: Texte à encoder
            use_cache: Utiliser le cache (défaut: True)
            
        Returns:
            EmbeddingResult ou None en cas d'erreur
        """
        if not text or len(text.strip()) < 3:
            logger.warning("Texte trop court pour générer un embedding")
            return None
        
        start_time = datetime.now()
        cache_key = self._compute_cache_key(text)
        
        # Vérifier le cache
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                return EmbeddingResult(
                    embedding=cached,
                    model=self.config.embedding_model,
                    cached=True,
                    generation_time_ms=0.0
                )
        
        # Générer via Ollama
        try:
            client = await self._get_client()
            
            # Tronquer si nécessaire (bge-m3 supporte 8K tokens)
            max_chars = self.config.embedding_max_tokens * self.config.chars_per_token
            truncated_text = text[:max_chars]
            
            response = await client.post(
                f"{self.config.ollama_url}/api/embeddings",
                json={
                    "model": self.config.embedding_model,
                    "prompt": truncated_text
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama embedding error: {response.status_code}")
                return None
            
            data = response.json()
            embedding = data.get("embedding", [])
            
            if not embedding:
                logger.error("Embedding vide retourné par Ollama")
                return None
            
            # Mettre en cache
            if use_cache:
                self._cache.put(cache_key, embedding)
            
            # Stats
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            self._total_generations += 1
            self._total_time_ms += elapsed_ms
            
            return EmbeddingResult(
                embedding=embedding,
                model=self.config.embedding_model,
                cached=False,
                generation_time_ms=elapsed_ms
            )
            
        except httpx.TimeoutException:
            logger.error(f"Timeout lors de la génération d'embedding ({self.config.embedding_timeout}s)")
            return None
        except Exception as e:
            logger.error(f"Erreur embedding: {e}")
            return None
    
    async def generate_batch(self, texts: List[str], use_cache: bool = True) -> List[Optional[EmbeddingResult]]:
        """
        Génère des embeddings pour plusieurs textes.
        
        Args:
            texts: Liste de textes à encoder
            use_cache: Utiliser le cache
            
        Returns:
            Liste de résultats (certains peuvent être None)
        """
        tasks = [self.generate(text, use_cache) for text in texts]
        return await asyncio.gather(*tasks)
    
    def clear_cache(self):
        """Vide le cache d'embeddings"""
        self._cache.clear()
        logger.info("Cache d'embeddings vidé")
    
    @property
    def stats(self) -> Dict:
        """Statistiques du service"""
        avg_time = (self._total_time_ms / self._total_generations) if self._total_generations > 0 else 0
        return {
            "model": self.config.embedding_model,
            "dimensions": self.config.embedding_dimensions,
            "total_generations": self._total_generations,
            "avg_generation_time_ms": f"{avg_time:.1f}",
            "cache": self._cache.stats
        }
    
    async def close(self):
        """Ferme le client HTTP"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton du service
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Obtient l'instance singleton du service d'embeddings"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


async def generate_embedding(text: str, use_cache: bool = True) -> Optional[List[float]]:
    """
    Fonction utilitaire pour générer un embedding.
    
    Args:
        text: Texte à encoder
        use_cache: Utiliser le cache
        
    Returns:
        Liste de floats (embedding) ou None
    """
    service = get_embedding_service()
    result = await service.generate(text, use_cache)
    return result.embedding if result else None
