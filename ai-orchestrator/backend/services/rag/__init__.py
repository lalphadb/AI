"""
RAG Apogée v2.0 - Architecture Professionnelle
Système de recherche sémantique multilingue avec reranking

Modules:
- config: Configuration centralisée
- embeddings: Service d'embeddings bge-m3 avec cache LRU
- reranker: Service de reranking cross-encoder
- search: Recherche hybride (dense + reranking)
- indexer: Indexation incrémentale avec tracking
- context_injector: Injection automatique dans les prompts

Usage:
    from services.rag import (
        search_documents,
        inject_rag_context,
        get_search_service,
        get_indexer,
        RAGConfig
    )
    
    # Recherche simple
    response = await search_documents("Comment installer Docker?")
    
    # Injection de contexte
    enriched_prompt, result = await inject_rag_context(system_prompt, user_query)
    
    # Indexation
    indexer = get_indexer()
    stats = await indexer.index_directory("/path/to/docs")
"""

from .config import (
    RAGConfig,
    get_rag_config,
    reset_config,
    EmbeddingModel,
    RerankerModel,
)

from .embeddings import (
    EmbeddingService,
    EmbeddingResult,
    get_embedding_service,
    generate_embedding,
)

from .reranker import (
    RerankerService,
    RerankResult,
    RerankStats,
    get_reranker_service,
)

from .search import (
    SearchService,
    SearchResult,
    SearchResponse,
    get_search_service,
    search_documents,
)

from .indexer import (
    DocumentIndexer,
    IndexingResult,
    IndexingStats,
    IndexedFile,
    get_indexer,
)

from .context_injector import (
    ContextInjector,
    InjectionResult,
    get_context_injector,
    inject_rag_context,
)


__all__ = [
    # Config
    "RAGConfig",
    "get_rag_config",
    "reset_config",
    "EmbeddingModel",
    "RerankerModel",
    # Embeddings
    "EmbeddingService",
    "EmbeddingResult",
    "get_embedding_service",
    "generate_embedding",
    # Reranker
    "RerankerService",
    "RerankResult",
    "RerankStats",
    "get_reranker_service",
    # Search
    "SearchService",
    "SearchResult",
    "SearchResponse",
    "get_search_service",
    "search_documents",
    # Indexer
    "DocumentIndexer",
    "IndexingResult",
    "IndexingStats",
    "IndexedFile",
    "get_indexer",
    # Context Injector
    "ContextInjector",
    "InjectionResult",
    "get_context_injector",
    "inject_rag_context",
]

__version__ = "2.0.0"
