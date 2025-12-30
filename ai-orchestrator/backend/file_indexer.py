#!/usr/bin/env python3
"""
File Indexer pour AI Orchestrator
Indexe automatiquement les fichiers importants dans la memoire semantique
Supporte le chunking pour les gros fichiers

Usage:
    python file_indexer.py --watch           # Mode watcher continu
    python file_indexer.py --index-all       # Indexer tous les fichiers configures
    python file_indexer.py --index path/file # Indexer un fichier specifique
"""

import argparse
import asyncio
import hashlib
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

import httpx

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    FileSystemEventHandler = object  # Fallback pour eviter NameError
    Observer = None

from document_chunker import chunk_file_content, count_tokens_approx

# Configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CHROMADB_HOST = os.getenv("CHROMADB_HOST", "chromadb")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8000"))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://10.10.10.46:11434")
EMBEDDING_MODEL = "mxbai-embed-large"
COLLECTION_NAME = "ai_orchestrator_memory_v2"

# Chemins a surveiller
WATCH_PATHS = [
    "/home/lalpha/projets/ai-tools/ai-orchestrator",
    "/home/lalpha/projets/infrastructure/unified-stack",
]

# Extensions a indexer
INDEXABLE_EXTENSIONS = {
    # Code
    ".py": "code",
    ".js": "code",
    ".ts": "code",
    ".jsx": "code",
    ".tsx": "code",
    ".go": "code",
    ".rs": "code",
    ".sh": "code",
    # Config
    ".yml": "config",
    ".yaml": "config",
    ".json": "config",
    ".toml": "config",
    ".env.example": "config",
    # Documentation
    ".md": "markdown",
    ".txt": "text",
    ".rst": "markdown",
}

# Fichiers a ignorer
IGNORE_PATTERNS = [
    "__pycache__",
    ".git",
    "node_modules",
    ".venv",
    "venv",
    ".pytest_cache",
    "*.pyc",
    "*.log",
    "*.backup",
    ".env",
    "package-lock.json",
    "yarn.lock",
]

# Taille max fichier (en bytes)
MAX_FILE_SIZE = 100 * 1024  # 100 KB

# Cache des fichiers indexes (hash -> timestamp)
_indexed_files: Dict[str, float] = {}


def should_ignore(path: str) -> bool:
    """Verifier si un fichier doit etre ignore"""
    path_lower = path.lower()
    for pattern in IGNORE_PATTERNS:
        if pattern.startswith("*"):
            if path_lower.endswith(pattern[1:]):
                return True
        elif pattern in path:
            return True
    return False


def get_file_type(path: str) -> Optional[str]:
    """Determiner le type de fichier"""
    ext = Path(path).suffix.lower()
    return INDEXABLE_EXTENSIONS.get(ext)


def get_file_hash(content: str) -> str:
    """Calculer hash du contenu"""
    return hashlib.md5(content.encode()).hexdigest()


async def get_embedding(text: str) -> Optional[List[float]]:
    """Obtenir embedding via Ollama"""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/embeddings", json={"model": EMBEDDING_MODEL, "prompt": text}
            )
            if response.status_code == 200:
                return response.json().get("embedding")
            else:
                logger.error(f"Embedding error: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return None


def get_chroma_collection():
    """Obtenir la collection ChromaDB"""
    import chromadb

    client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
    return client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"description": "Memoire semantique AI Orchestrator v2"}
    )


async def index_file(filepath: str, force: bool = False) -> bool:
    """
    Indexer un fichier dans ChromaDB

    Args:
        filepath: Chemin du fichier
        force: Forcer re-indexation meme si deja indexe

    Returns:
        True si indexe avec succes
    """
    global _indexed_files

    # Verifications
    if not os.path.exists(filepath):
        logger.warning(f"Fichier non trouve: {filepath}")
        return False

    if should_ignore(filepath):
        logger.debug(f"Ignore: {filepath}")
        return False

    file_type = get_file_type(filepath)
    if not file_type:
        logger.debug(f"Type non supporte: {filepath}")
        return False

    # Verifier taille
    file_size = os.path.getsize(filepath)
    if file_size > MAX_FILE_SIZE:
        logger.warning(f"Fichier trop gros ({file_size} bytes): {filepath}")
        return False

    if file_size == 0:
        logger.debug(f"Fichier vide: {filepath}")
        return False

    # Lire contenu
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Erreur lecture {filepath}: {e}")
        return False

    # Verifier si deja indexe (meme contenu)
    content_hash = get_file_hash(content)
    if not force and content_hash in _indexed_files:
        logger.debug(f"Deja indexe (meme contenu): {filepath}")
        return False

    # Chunker le fichier
    relative_path = filepath
    for watch_path in WATCH_PATHS:
        if filepath.startswith(watch_path):
            relative_path = filepath[len(watch_path) :].lstrip("/")
            break

    chunks = chunk_file_content(
        content=content,
        filename=relative_path,
        file_type=file_type,
        chunk_size=400,  # ~1600 chars
        overlap=40,  # ~160 chars
    )

    if not chunks:
        logger.debug(f"Aucun chunk genere: {filepath}")
        return False

    # Indexer dans ChromaDB
    try:
        collection = get_chroma_collection()

        for chunk in chunks:
            # Generer embedding
            embed_text = f"{file_type}: {relative_path} - {chunk['content'][:500]}"
            embedding = await get_embedding(embed_text)

            if not embedding:
                logger.warning(f"Embedding echoue pour chunk {chunk['id']}")
                continue

            # Enrichir metadata
            chunk["metadata"].update(
                {
                    "indexed_at": datetime.now().isoformat(),
                    "content_hash": content_hash,
                    "embedding_model": EMBEDDING_MODEL,
                }
            )

            # Upsert
            collection.upsert(
                ids=[chunk["id"]],
                documents=[chunk["content"]],
                embeddings=[embedding],
                metadatas=[chunk["metadata"]],
            )

        # Marquer comme indexe
        _indexed_files[content_hash] = time.time()

        logger.info(
            f"✅ Indexe: {relative_path} ({len(chunks)} chunks, {count_tokens_approx(content)} tokens)"
        )
        return True

    except Exception as e:
        logger.error(f"Erreur indexation {filepath}: {e}")
        return False


async def index_directory(directory: str, recursive: bool = True) -> int:
    """
    Indexer tous les fichiers d'un repertoire

    Returns:
        Nombre de fichiers indexes
    """
    indexed_count = 0
    directory = os.path.expanduser(directory)

    if not os.path.isdir(directory):
        logger.error(f"Repertoire non trouve: {directory}")
        return 0

    for root, dirs, files in os.walk(directory):
        # Filtrer les dossiers a ignorer
        dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d))]

        for filename in files:
            filepath = os.path.join(root, filename)
            if await index_file(filepath):
                indexed_count += 1

        if not recursive:
            break

    return indexed_count


async def index_all_configured() -> int:
    """Indexer tous les chemins configures"""
    total = 0
    for path in WATCH_PATHS:
        logger.info(f"Indexation de {path}...")
        count = await index_directory(path)
        total += count
        logger.info(f"  -> {count} fichiers indexes")
    return total


class FileIndexerHandler(FileSystemEventHandler):
    """Handler pour watchdog"""

    def __init__(self, loop):
        self.loop = loop
        self._debounce: Dict[str, float] = {}
        self._debounce_delay = 2.0  # secondes

    def _should_process(self, path: str) -> bool:
        """Debounce pour eviter indexations multiples"""
        now = time.time()
        last = self._debounce.get(path, 0)
        if now - last < self._debounce_delay:
            return False
        self._debounce[path] = now
        return True

    def on_modified(self, event):
        if event.is_directory:
            return
        if not self._should_process(event.src_path):
            return
        asyncio.run_coroutine_threadsafe(index_file(event.src_path), self.loop)

    def on_created(self, event):
        if event.is_directory:
            return
        if not self._should_process(event.src_path):
            return
        asyncio.run_coroutine_threadsafe(index_file(event.src_path), self.loop)


async def watch_directories():
    """Mode watch: surveiller les modifications"""
    if not WATCHDOG_AVAILABLE:
        logger.error("watchdog non disponible. Installer avec: pip install watchdog")
        return

    loop = asyncio.get_event_loop()
    observer = Observer()
    handler = FileIndexerHandler(loop)

    for path in WATCH_PATHS:
        if os.path.exists(path):
            observer.schedule(handler, path, recursive=True)
            logger.info(f"👁️ Surveillance: {path}")
        else:
            logger.warning(f"Chemin non trouve: {path}")

    observer.start()
    logger.info("🚀 File Indexer demarre en mode watch")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("Arret du watcher")

    observer.join()


def main():
    parser = argparse.ArgumentParser(description="File Indexer pour AI Orchestrator")
    parser.add_argument("--watch", action="store_true", help="Mode surveillance continue")
    parser.add_argument(
        "--index-all", action="store_true", help="Indexer tous les chemins configures"
    )
    parser.add_argument("--index", type=str, help="Indexer un fichier ou repertoire specifique")
    parser.add_argument("--force", action="store_true", help="Forcer re-indexation")

    args = parser.parse_args()

    if args.watch:
        asyncio.run(watch_directories())
    elif args.index_all:
        count = asyncio.run(index_all_configured())
        print(f"\n✅ Total: {count} fichiers indexes")
    elif args.index:
        path = os.path.expanduser(args.index)
        if os.path.isdir(path):
            count = asyncio.run(index_directory(path))
            print(f"✅ {count} fichiers indexes")
        else:
            success = asyncio.run(index_file(path, force=args.force))
            print(f"{'✅' if success else '❌'} {path}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
