"""
RAG Apogée v2.0 - Service de Reranking
Réordonne les résultats par pertinence avec cross-encoder
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

import httpx

from .config import RAGConfig, RerankerModel, get_rag_config

logger = logging.getLogger("rag.reranker")


@dataclass
class RerankResult:
    """Résultat d'un document après reranking"""
    content: str
    metadata: dict
    original_score: float
    rerank_score: float
    combined_score: float


@dataclass
class RerankStats:
    """Statistiques d'une opération de reranking"""
    input_count: int
    output_count: int
    rerank_time_ms: float
    model: str


class RerankerService:
    """
    Service de reranking cross-encoder.

    Utilise bge-reranker-v2-m3 via Ollama pour calculer des scores
    de pertinence query-document plus précis qu'une simple similarité.
    """

    def __init__(self, config: RAGConfig | None = None):
        self.config = config or get_rag_config()
        self._client: httpx.AsyncClient | None = None
        self._total_reranks = 0
        self._total_time_ms = 0.0
        self._enabled = self.config.reranker_model != RerankerModel.NONE.value

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy initialization du client HTTP"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.config.rerank_timeout)
        return self._client

    async def _compute_rerank_score(self, query: str, document: str) -> float:
        """
        Calcule le score de pertinence query-document via cross-encoder.

        Le modèle bge-reranker génère un embedding dont la magnitude
        représente le score de pertinence.
        """
        if not self._enabled:
            return 0.5  # Score neutre si reranker désactivé

        # Format cross-encoder
        combined = f"Query: {query}\nDocument: {document[:2000]}"

        try:
            client = await self._get_client()

            response = await client.post(
                f"{self.config.ollama_url}/api/embeddings",
                json={
                    "model": self.config.reranker_model,
                    "prompt": combined
                }
            )

            if response.status_code != 200:
                logger.warning(f"Reranker error: {response.status_code}")
                return 0.5

            data = response.json()
            embedding = data.get("embedding", [])

            if not embedding:
                return 0.5

            # Score basé sur la magnitude des premiers composants
            # Normalisation entre 0 et 1
            raw_score = sum(abs(x) for x in embedding[:100]) / 100
            normalized_score = min(1.0, max(0.0, raw_score))

            return normalized_score

        except httpx.TimeoutException:
            logger.warning("Timeout reranker")
            return 0.5
        except Exception as e:
            logger.warning(f"Erreur reranker: {e}")
            return 0.5

    def _distance_to_similarity(self, distance: float) -> float:
        """
        Convertit une distance L2 en score de similarité [0, 1].

        Formule: similarity = 1 / (1 + distance)
        """
        return 1.0 / (1.0 + distance)

    async def rerank(
        self,
        query: str,
        documents: list[tuple[str, dict, float]],
        top_k: int | None = None
    ) -> tuple[list[RerankResult], RerankStats]:
        """
        Réordonne les documents par pertinence.

        Args:
            query: Requête utilisateur
            documents: Liste de (content, metadata, distance_score)
            top_k: Nombre de résultats à retourner (défaut: config.rerank_top_k)

        Returns:
            Tuple (résultats rerankés, statistiques)
        """
        if top_k is None:
            top_k = self.config.rerank_top_k

        start_time = datetime.now()
        results = []

        # Calculer les scores de reranking en parallèle
        rerank_tasks = []
        for content, metadata, distance in documents:
            if self._enabled:
                task = self._compute_rerank_score(query, content)
            else:
                # Fallback: utiliser la distance convertie en similarité
                task = asyncio.coroutine(lambda d=distance: self._distance_to_similarity(d))()
            rerank_tasks.append(task)

        rerank_scores = await asyncio.gather(*rerank_tasks)

        # Combiner les scores
        for (content, metadata, distance), rerank_score in zip(documents, rerank_scores, strict=False):
            similarity_score = self._distance_to_similarity(distance)

            # Score combiné: 60% reranker + 40% similarité dense
            combined = (0.6 * rerank_score) + (0.4 * similarity_score)

            results.append(RerankResult(
                content=content,
                metadata=metadata,
                original_score=similarity_score,
                rerank_score=rerank_score,
                combined_score=combined
            ))

        # Trier par score combiné décroissant
        results.sort(key=lambda x: x.combined_score, reverse=True)

        # Filtrer par score minimum
        filtered_results = [
            r for r in results
            if r.combined_score >= self.config.min_relevance_score
        ]

        # Garder top_k
        final_results = filtered_results[:top_k]

        # Stats
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        self._total_reranks += 1
        self._total_time_ms += elapsed_ms

        stats = RerankStats(
            input_count=len(documents),
            output_count=len(final_results),
            rerank_time_ms=elapsed_ms,
            model=self.config.reranker_model if self._enabled else "similarity_only"
        )

        logger.debug(f"Reranked {len(documents)} -> {len(final_results)} docs in {elapsed_ms:.0f}ms")

        return final_results, stats

    @property
    def stats(self) -> dict:
        """Statistiques du service"""
        avg_time = (self._total_time_ms / self._total_reranks) if self._total_reranks > 0 else 0
        return {
            "enabled": self._enabled,
            "model": self.config.reranker_model,
            "total_reranks": self._total_reranks,
            "avg_time_ms": f"{avg_time:.1f}"
        }

    async def close(self):
        """Ferme le client HTTP"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton
_reranker_service: RerankerService | None = None


def get_reranker_service() -> RerankerService:
    """Obtient l'instance singleton du service de reranking"""
    global _reranker_service
    if _reranker_service is None:
        _reranker_service = RerankerService()
    return _reranker_service
