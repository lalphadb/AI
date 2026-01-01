"""
RAG Apogée v2.0 - Configuration centralisée
Toutes les constantes et paramètres du système RAG
"""

import os
from dataclasses import dataclass, field
from enum import Enum


class EmbeddingModel(Enum):
    """Modèles d'embedding supportés"""
    BGE_M3 = "bge-m3"
    MXBAI = "mxbai-embed-large"
    NOMIC = "nomic-embed-text"


class RerankerModel(Enum):
    """Modèles de reranking supportés"""
    BGE_RERANKER_V2 = "qllama/bge-reranker-v2-m3"
    NONE = "none"


@dataclass
class RAGConfig:
    """Configuration principale du système RAG"""

    # === Connexions ===
    ollama_url: str = field(default_factory=lambda: os.getenv("OLLAMA_URL", "http://10.10.10.46:11434"))
    chromadb_host: str = field(default_factory=lambda: os.getenv("CHROMADB_HOST", "chromadb"))
    chromadb_port: int = field(default_factory=lambda: int(os.getenv("CHROMADB_PORT", "8000")))

    # === Modèles ===
    embedding_model: str = field(default_factory=lambda: os.getenv("RAG_EMBEDDING_MODEL", EmbeddingModel.BGE_M3.value))
    reranker_model: str = field(default_factory=lambda: os.getenv("RAG_RERANKER_MODEL", RerankerModel.BGE_RERANKER_V2.value))

    # === Collection ===
    collection_name: str = field(default_factory=lambda: os.getenv("RAG_COLLECTION", "ai_orchestrator_memory_v3"))

    # === Embedding ===
    embedding_dimensions: int = 1024
    embedding_max_tokens: int = 8192
    embedding_cache_size: int = 1000

    # === Chunking ===
    chunk_size_tokens: int = 768
    chunk_overlap_percent: float = 0.15
    chars_per_token: int = 4
    min_chunk_size: int = 100

    # === Recherche ===
    default_top_k: int = 5
    retrieval_top_k: int = 20  # Récupérer plus pour le reranking
    rerank_top_k: int = 5      # Garder les meilleurs après reranking
    min_relevance_score: float = 0.3

    # === Injection contexte ===
    context_injection_enabled: bool = True
    context_max_chars: int = 4000
    context_min_score: float = 0.25

    # === Indexation incrémentale ===
    index_tracking_file: str = "/data/rag_index_tracking.json"
    auto_reindex_on_change: bool = True

    # === Timeouts (secondes) ===
    embedding_timeout: float = 60.0
    rerank_timeout: float = 30.0
    search_timeout: float = 30.0
    index_timeout: float = 120.0

    @property
    def chromadb_url(self) -> str:
        return f"http://{self.chromadb_host}:{self.chromadb_port}"

    @property
    def chunk_size_chars(self) -> int:
        return self.chunk_size_tokens * self.chars_per_token

    @property
    def chunk_overlap_chars(self) -> int:
        return int(self.chunk_size_chars * self.chunk_overlap_percent)


@dataclass
class IndexedDocument:
    """Représentation d'un document indexé"""
    doc_id: str
    source: str
    filename: str
    topic: str
    content_hash: str
    chunk_index: int
    total_chunks: int
    content_length: int
    indexed_at: str
    embedding_model: str


# Instance globale de configuration
_config: RAGConfig | None = None


def get_rag_config() -> RAGConfig:
    """Singleton pour la configuration RAG"""
    global _config
    if _config is None:
        _config = RAGConfig()
    return _config


def reset_config():
    """Reset la configuration (pour les tests)"""
    global _config
    _config = None
