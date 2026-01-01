"""
RAG Apogée v2.0 - Injecteur de Contexte
Injection automatique du contexte RAG dans les prompts
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime

from .config import RAGConfig, get_rag_config
from .search import SearchResult, SearchService, get_search_service

logger = logging.getLogger("rag.context_injector")


@dataclass
class InjectionResult:
    """Résultat d'une injection de contexte"""
    context: str | None
    sources: list[str]
    relevance_score: float
    search_time_ms: float
    injected: bool


class ContextInjector:
    """
    Service d'injection automatique de contexte RAG.

    Analyse la requête utilisateur et injecte le contexte pertinent
    de la base de connaissances dans le prompt système.
    """

    def __init__(
        self,
        config: RAGConfig | None = None,
        search_service: SearchService | None = None
    ):
        self.config = config or get_rag_config()
        self._search_service = search_service

    @property
    def search_service(self) -> SearchService:
        if self._search_service is None:
            self._search_service = get_search_service()
        return self._search_service

    def _should_inject_context(self, query: str) -> bool:
        """
        Détermine si le contexte doit être injecté pour cette requête.

        Évite l'injection pour:
        - Questions très courtes
        - Salutations simples
        - Commandes système
        """
        if not self.config.context_injection_enabled:
            return False

        query_lower = query.lower().strip()

        # Requêtes trop courtes
        if len(query_lower) < 10:
            return False

        # Salutations simples
        greetings = ["bonjour", "salut", "hello", "hi", "hey", "coucou", "bonsoir"]
        if query_lower in greetings or query_lower.rstrip('!') in greetings:
            return False

        # Commandes système
        if query_lower.startswith(("exit", "quit", "bye", "clear", "help")):
            return False

        return True

    def _extract_keywords(self, query: str) -> list[str]:
        """
        Extrait les mots-clés importants de la requête.

        Utilisé pour enrichir la recherche.
        """
        # Stopwords français
        stopwords = {
            "le", "la", "les", "un", "une", "des", "du", "de", "et", "ou",
            "à", "au", "aux", "en", "dans", "sur", "pour", "par", "avec",
            "ce", "cette", "ces", "mon", "ma", "mes", "ton", "ta", "tes",
            "son", "sa", "ses", "notre", "nos", "votre", "vos", "leur", "leurs",
            "qui", "que", "quoi", "dont", "où", "comment", "pourquoi", "quand",
            "est", "sont", "être", "avoir", "fait", "faire", "peut", "peux",
            "je", "tu", "il", "elle", "nous", "vous", "ils", "elles",
            "me", "te", "se", "lui", "y", "ne", "pas", "plus", "moins",
            "très", "bien", "mal", "aussi", "comme", "alors", "donc", "si"
        }

        # Nettoyer et tokeniser
        words = re.findall(r'\b\w+\b', query.lower())

        # Filtrer
        keywords = [w for w in words if w not in stopwords and len(w) > 2]

        return keywords

    def _format_context(self, results: list[SearchResult]) -> str:
        """
        Formate les résultats de recherche en contexte injecté.
        """
        if not results:
            return ""

        parts = ["## 📚 Contexte de la base de connaissances:\n"]

        for _i, result in enumerate(results, 1):
            # Tronquer le contenu si nécessaire
            content = result.content
            if len(content) > 800:
                content = content[:800] + "..."

            score_pct = int(result.score * 100)
            parts.append(f"**[{result.filename}]** ({result.topic}, {score_pct}% pertinent):")
            parts.append(content)
            parts.append("")

        return "\n".join(parts)

    async def get_context_for_query(
        self,
        query: str,
        max_results: int = 3
    ) -> InjectionResult:
        """
        Obtient le contexte pertinent pour une requête.

        Args:
            query: Requête utilisateur
            max_results: Nombre maximum de résultats

        Returns:
            InjectionResult
        """
        start_time = datetime.now()

        # Vérifier si injection nécessaire
        if not self._should_inject_context(query):
            return InjectionResult(
                context=None,
                sources=[],
                relevance_score=0.0,
                search_time_ms=0.0,
                injected=False
            )

        try:
            # Rechercher dans la base
            response = await self.search_service.search(
                query=query,
                top_k=max_results,
                use_reranking=True
            )

            search_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            if not response.results:
                return InjectionResult(
                    context=None,
                    sources=[],
                    relevance_score=0.0,
                    search_time_ms=search_time_ms,
                    injected=False
                )

            # Filtrer par score minimum
            relevant_results = [
                r for r in response.results
                if r.score >= self.config.context_min_score
            ]

            if not relevant_results:
                logger.debug(f"Pas de résultats assez pertinents (min: {self.config.context_min_score})")
                return InjectionResult(
                    context=None,
                    sources=[],
                    relevance_score=0.0,
                    search_time_ms=search_time_ms,
                    injected=False
                )

            # Calculer le score moyen
            avg_score = sum(r.score for r in relevant_results) / len(relevant_results)

            # Formater le contexte
            context = self._format_context(relevant_results)

            # Limiter la taille
            if len(context) > self.config.context_max_chars:
                context = context[:self.config.context_max_chars] + "\n..."

            sources = [r.source for r in relevant_results]

            logger.info(f"Contexte injecté: {len(relevant_results)} docs, score moyen: {avg_score:.2f}")

            return InjectionResult(
                context=context,
                sources=sources,
                relevance_score=avg_score,
                search_time_ms=search_time_ms,
                injected=True
            )

        except Exception as e:
            logger.error(f"Erreur injection contexte: {e}")
            return InjectionResult(
                context=None,
                sources=[],
                relevance_score=0.0,
                search_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                injected=False
            )

    async def inject_into_prompt(
        self,
        system_prompt: str,
        user_query: str
    ) -> tuple[str, InjectionResult]:
        """
        Injecte le contexte RAG dans le prompt système.

        Args:
            system_prompt: Prompt système original
            user_query: Requête utilisateur

        Returns:
            Tuple (prompt enrichi, résultat d'injection)
        """
        result = await self.get_context_for_query(user_query)

        if not result.injected or not result.context:
            return system_prompt, result

        # Injecter le contexte à la fin du prompt système
        enriched_prompt = f"{system_prompt}\n\n{result.context}"

        return enriched_prompt, result


# Singleton
_context_injector: ContextInjector | None = None


def get_context_injector() -> ContextInjector:
    """Obtient l'instance singleton de l'injecteur de contexte"""
    global _context_injector
    if _context_injector is None:
        _context_injector = ContextInjector()
    return _context_injector


async def inject_rag_context(
    system_prompt: str,
    user_query: str
) -> tuple[str, InjectionResult]:
    """
    Fonction utilitaire pour injecter le contexte RAG.

    Args:
        system_prompt: Prompt système original
        user_query: Requête utilisateur

    Returns:
        Tuple (prompt enrichi, résultat d'injection)
    """
    injector = get_context_injector()
    return await injector.inject_into_prompt(system_prompt, user_query)
