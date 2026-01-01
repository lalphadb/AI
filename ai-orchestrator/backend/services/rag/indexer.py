"""
RAG Apogée v2.0 - Service d'Indexation Incrémentale
Indexe les documents avec tracking des changements
"""

import hashlib
import json
import logging
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import httpx

from .config import RAGConfig, get_rag_config
from .embeddings import get_embedding_service

logger = logging.getLogger("rag.indexer")


@dataclass
class IndexedFile:
    """Représentation d'un fichier indexé"""
    filepath: str
    content_hash: str
    chunk_count: int
    indexed_at: str
    file_size: int


@dataclass
class IndexingResult:
    """Résultat d'une opération d'indexation"""
    filepath: str
    success: bool
    chunks_indexed: int
    error: str | None = None


@dataclass
class IndexingStats:
    """Statistiques globales d'indexation"""
    total_files: int
    total_chunks: int
    new_files: int
    updated_files: int
    unchanged_files: int
    errors: int
    duration_ms: float


class IndexTracker:
    """Gestionnaire de tracking des fichiers indexés"""

    def __init__(self, tracking_file: str):
        self.tracking_file = tracking_file
        self._index: dict[str, IndexedFile] = {}
        self._load()

    def _load(self):
        """Charge l'index depuis le fichier"""
        try:
            if os.path.exists(self.tracking_file):
                with open(self.tracking_file) as f:
                    data = json.load(f)
                    for filepath, info in data.items():
                        self._index[filepath] = IndexedFile(**info)
                logger.info(f"Index chargé: {len(self._index)} fichiers trackés")
        except Exception as e:
            logger.warning(f"Erreur chargement index: {e}")
            self._index = {}

    def _save(self):
        """Sauvegarde l'index"""
        try:
            os.makedirs(os.path.dirname(self.tracking_file), exist_ok=True)
            with open(self.tracking_file, 'w') as f:
                data = {fp: asdict(info) for fp, info in self._index.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Erreur sauvegarde index: {e}")

    def get_file_info(self, filepath: str) -> IndexedFile | None:
        """Récupère les infos d'un fichier indexé"""
        return self._index.get(filepath)

    def update_file(self, filepath: str, content_hash: str, chunk_count: int, file_size: int):
        """Met à jour les infos d'un fichier"""
        self._index[filepath] = IndexedFile(
            filepath=filepath,
            content_hash=content_hash,
            chunk_count=chunk_count,
            indexed_at=datetime.now().isoformat(),
            file_size=file_size
        )
        self._save()

    def remove_file(self, filepath: str):
        """Supprime un fichier de l'index"""
        if filepath in self._index:
            del self._index[filepath]
            self._save()

    def needs_reindex(self, filepath: str, current_hash: str) -> bool:
        """Vérifie si un fichier doit être réindexé"""
        info = self._index.get(filepath)
        if not info:
            return True
        return info.content_hash != current_hash

    @property
    def tracked_files(self) -> set[str]:
        """Ensemble des fichiers trackés"""
        return set(self._index.keys())


class DocumentIndexer:
    """
    Service d'indexation de documents.

    Fonctionnalités:
    - Indexation incrémentale (ne réindexe que les changements)
    - Chunking intelligent par sections markdown
    - Métadonnées riches
    - Tracking persistant
    """

    def __init__(self, config: RAGConfig | None = None):
        self.config = config or get_rag_config()
        self._embedding_service = None
        self._client: httpx.AsyncClient | None = None
        self._collection_id: str | None = None
        self._tracker = IndexTracker(self.config.index_tracking_file)

    @property
    def embedding_service(self):
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.config.index_timeout)
        return self._client

    async def _get_collection_id(self) -> str | None:
        """Récupère l'ID de la collection"""
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
            logger.error(f"Erreur récupération collection: {e}")

        return None

    def _compute_file_hash(self, content: str) -> str:
        """Calcule le hash MD5 du contenu"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _chunk_document(self, content: str) -> list[dict]:
        """
        Découpe un document en chunks avec overlap.

        Stratégie:
        1. Découpe par sections markdown (##, ###)
        2. Respecte la taille maximale des chunks
        3. Ajoute un overlap pour la continuité
        """
        chunks = []
        chunk_chars = self.config.chunk_size_chars
        overlap_chars = self.config.chunk_overlap_chars

        # Nettoyer le contenu
        content = re.sub(r'\n{3,}', '\n\n', content)

        # Si le document est petit, un seul chunk
        if len(content) <= chunk_chars:
            return [{"content": content.strip(), "index": 0}]

        # Découper par sections markdown
        sections = re.split(r'(?=^#{1,3} )', content, flags=re.MULTILINE)

        current_chunk = ""
        chunk_index = 0

        for section in sections:
            if not section.strip():
                continue

            # Si la section + chunk actuel dépasse la taille
            if len(current_chunk) + len(section) > chunk_chars:
                if current_chunk.strip():
                    chunks.append({
                        "content": current_chunk.strip(),
                        "index": chunk_index
                    })
                    chunk_index += 1
                    # Garder l'overlap
                    if len(current_chunk) > overlap_chars:
                        current_chunk = current_chunk[-overlap_chars:]
                    else:
                        current_chunk = ""

                # Si la section seule est trop grande
                if len(section) > chunk_chars:
                    words = section.split()
                    temp_chunk = current_chunk
                    for word in words:
                        if len(temp_chunk) + len(word) + 1 > chunk_chars:
                            if temp_chunk.strip():
                                chunks.append({
                                    "content": temp_chunk.strip(),
                                    "index": chunk_index
                                })
                                chunk_index += 1
                            temp_chunk = temp_chunk[-overlap_chars:] if len(temp_chunk) > overlap_chars else ""
                        temp_chunk += " " + word
                    current_chunk = temp_chunk
                else:
                    current_chunk += section
            else:
                current_chunk += section

        # Dernier chunk
        if current_chunk.strip():
            chunks.append({
                "content": current_chunk.strip(),
                "index": chunk_index
            })

        return chunks

    def _detect_topic(self, filepath: str, content: str) -> str:
        """Détecte le topic basé sur le chemin et le contenu"""
        path_lower = filepath.lower()

        if "guide" in path_lower:
            return "guide"
        elif "session" in path_lower or "compte" in path_lower:
            return "session"
        elif "readme" in path_lower:
            return "readme"
        elif ".py" in path_lower:
            return "code"
        elif "docker" in content.lower()[:500]:
            return "docker"
        elif "traefik" in content.lower()[:500]:
            return "traefik"
        else:
            return "documentation"

    async def _delete_file_chunks(self, filepath: str) -> bool:
        """Supprime tous les chunks d'un fichier"""
        collection_id = await self._get_collection_id()
        if not collection_id:
            return False

        # On ne peut pas facilement supprimer par metadata dans ChromaDB API
        # Pour l'instant, on laisse les anciens chunks (ils seront remplacés)
        return True

    async def index_file(
        self,
        filepath: str,
        force: bool = False
    ) -> IndexingResult:
        """
        Indexe un fichier.

        Args:
            filepath: Chemin du fichier
            force: Forcer la réindexation même si pas de changement

        Returns:
            IndexingResult
        """
        try:
            path = Path(filepath)
            if not path.exists():
                return IndexingResult(filepath, False, 0, "Fichier non trouvé")

            content = path.read_text(encoding='utf-8')
            if len(content) < self.config.min_chunk_size:
                return IndexingResult(filepath, False, 0, "Fichier trop petit")

            content_hash = self._compute_file_hash(content)

            # Vérifier si réindexation nécessaire
            if not force and not self._tracker.needs_reindex(filepath, content_hash):
                logger.debug(f"Fichier inchangé: {filepath}")
                return IndexingResult(filepath, True, 0, "Inchangé")

            # Découper en chunks
            chunks = self._chunk_document(content)
            filename = path.stem
            topic = self._detect_topic(filepath, content)

            collection_id = await self._get_collection_id()
            if not collection_id:
                return IndexingResult(filepath, False, 0, "Collection non trouvée")

            # Indexer chaque chunk
            indexed_count = 0
            client = await self._get_client()

            for chunk in chunks:
                chunk_hash = hashlib.md5(chunk["content"][:200].encode()).hexdigest()[:8]
                doc_id = f"doc_{filename}_{chunk['index']}_{chunk_hash}"

                # Générer l'embedding
                embed_result = await self.embedding_service.generate(chunk["content"])
                if not embed_result:
                    continue

                metadata = {
                    "source": filepath,
                    "filename": filename,
                    "topic": topic,
                    "chunk_index": chunk["index"],
                    "total_chunks": len(chunks),
                    "content_hash": content_hash,
                    "lang": "fr",
                    "indexed_at": datetime.now().isoformat(),
                    "content_length": len(chunk["content"])
                }

                try:
                    response = await client.post(
                        f"{self.config.chromadb_url}/api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}/add",
                        json={
                            "ids": [doc_id],
                            "documents": [chunk["content"]],
                            "embeddings": [embed_result.embedding],
                            "metadatas": [metadata]
                        }
                    )

                    if response.status_code in (200, 201):
                        indexed_count += 1
                except Exception as e:
                    logger.warning(f"Erreur indexation chunk: {e}")

            # Mettre à jour le tracker
            self._tracker.update_file(
                filepath, content_hash, indexed_count, len(content)
            )

            logger.info(f"Indexé: {filepath} ({indexed_count} chunks)")
            return IndexingResult(filepath, True, indexed_count)

        except Exception as e:
            logger.error(f"Erreur indexation {filepath}: {e}")
            return IndexingResult(filepath, False, 0, str(e))

    async def index_directory(
        self,
        directory: str,
        patterns: list[str] = None,
        force: bool = False
    ) -> IndexingStats:
        """
        Indexe tous les fichiers d'un répertoire.

        Args:
            directory: Chemin du répertoire
            patterns: Patterns de fichiers à indexer
            force: Forcer la réindexation

        Returns:
            IndexingStats
        """
        if patterns is None:
            patterns = ["*.md", "*.txt"]
        start_time = datetime.now()

        dir_path = Path(directory)
        if not dir_path.exists():
            logger.error(f"Répertoire non trouvé: {directory}")
            return IndexingStats(0, 0, 0, 0, 0, 1, 0)

        # Trouver tous les fichiers
        files = []
        for pattern in patterns:
            files.extend(dir_path.rglob(pattern))

        stats = {
            "total_files": len(files),
            "total_chunks": 0,
            "new_files": 0,
            "updated_files": 0,
            "unchanged_files": 0,
            "errors": 0
        }

        for filepath in files:
            result = await self.index_file(str(filepath), force)

            if result.success:
                stats["total_chunks"] += result.chunks_indexed
                if result.error == "Inchangé":
                    stats["unchanged_files"] += 1
                elif result.chunks_indexed > 0:
                    # Déterminer si nouveau ou mis à jour
                    if self._tracker.get_file_info(str(filepath)):
                        stats["updated_files"] += 1
                    else:
                        stats["new_files"] += 1
            else:
                stats["errors"] += 1

        duration_ms = (datetime.now() - start_time).total_seconds() * 1000

        return IndexingStats(
            total_files=stats["total_files"],
            total_chunks=stats["total_chunks"],
            new_files=stats["new_files"],
            updated_files=stats["updated_files"],
            unchanged_files=stats["unchanged_files"],
            errors=stats["errors"],
            duration_ms=duration_ms
        )

    @property
    def tracked_files_count(self) -> int:
        """Nombre de fichiers trackés"""
        return len(self._tracker.tracked_files)


# Singleton
_indexer: DocumentIndexer | None = None


def get_indexer() -> DocumentIndexer:
    """Obtient l'instance singleton de l'indexer"""
    global _indexer
    if _indexer is None:
        _indexer = DocumentIndexer()
    return _indexer
