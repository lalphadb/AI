#!/usr/bin/env python3
"""
Script d'indexation de la documentation avec bge-m3
Indexe tous les fichiers .md dans ChromaDB v3
"""

import asyncio
import hashlib
import os
import re
from pathlib import Path
from datetime import datetime
import httpx

# Configuration
OLLAMA_URL = "http://localhost:11434"
CHROMADB_URL = "http://localhost:8000"
EMBEDDING_MODEL = "bge-m3"
COLLECTION_ID = "a1769fcb-b07e-4e9e-8d75-cc18ee80a3c6"
DOC_DIR = "/home/lalpha/documentation"

# Chunking config
CHUNK_SIZE = 768  # tokens (~3000 chars)
CHUNK_OVERLAP = 115  # 15%
CHARS_PER_TOKEN = 4

# Stats
stats = {"files": 0, "chunks": 0, "errors": 0, "skipped": 0}


def chunk_text(text: str, source: str) -> list:
    """Découpe le texte en chunks avec overlap"""
    chunks = []
    
    # Taille en caractères
    chunk_chars = CHUNK_SIZE * CHARS_PER_TOKEN
    overlap_chars = CHUNK_OVERLAP * CHARS_PER_TOKEN
    
    # Nettoyer le texte
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Si le texte est petit, un seul chunk
    if len(text) <= chunk_chars:
        return [{"content": text.strip(), "index": 0}]
    
    # Découper par sections (headers markdown)
    sections = re.split(r'(?=^#{1,3} )', text, flags=re.MULTILINE)
    
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
                current_chunk = current_chunk[-overlap_chars:] if len(current_chunk) > overlap_chars else ""
            
            # Si la section seule est trop grande, la découper
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


async def get_embedding(text: str) -> list:
    """Obtenir l'embedding via bge-m3"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": EMBEDDING_MODEL, "prompt": text[:8000]}  # Limite 8K tokens
            )
            if r.status_code == 200:
                return r.json().get("embedding", [])
    except Exception as e:
        print(f"  ⚠️ Erreur embedding: {e}")
    return []


async def index_chunk(doc_id: str, content: str, metadata: dict) -> bool:
    """Indexer un chunk dans ChromaDB"""
    embedding = await get_embedding(content)
    if not embedding:
        return False
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{CHROMADB_URL}/api/v2/tenants/default_tenant/databases/default_database/collections/{COLLECTION_ID}/add",
                json={
                    "ids": [doc_id],
                    "documents": [content],
                    "embeddings": [embedding],
                    "metadatas": [metadata]
                }
            )
            return r.status_code in (200, 201)
    except Exception as e:
        print(f"  ⚠️ Erreur indexation: {e}")
        return False


async def process_file(filepath: Path) -> int:
    """Traiter un fichier et l'indexer"""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  ❌ Erreur lecture {filepath.name}: {e}")
        stats["errors"] += 1
        return 0
    
    # Skip si trop petit
    if len(content) < 100:
        stats["skipped"] += 1
        return 0
    
    # Extraire les métadonnées
    relative_path = str(filepath.relative_to(DOC_DIR))
    filename = filepath.stem
    
    # Déterminer le topic basé sur le chemin
    if "guides" in relative_path:
        topic = "guide"
    elif "comptes-rendus" in relative_path:
        topic = "session"
    elif "archives" in relative_path:
        topic = "archive"
    else:
        topic = "documentation"
    
    # Découper en chunks
    chunks = chunk_text(content, relative_path)
    
    print(f"  📄 {filename}: {len(chunks)} chunks")
    
    indexed = 0
    for chunk in chunks:
        # ID unique basé sur le contenu
        content_hash = hashlib.md5(chunk["content"][:500].encode()).hexdigest()[:12]
        doc_id = f"doc_{filename}_{chunk['index']}_{content_hash}"
        
        metadata = {
            "source": relative_path,
            "filename": filename,
            "topic": topic,
            "chunk_index": chunk["index"],
            "total_chunks": len(chunks),
            "lang": "fr",
            "indexed_at": datetime.now().isoformat(),
            "content_length": len(chunk["content"])
        }
        
        if await index_chunk(doc_id, chunk["content"], metadata):
            indexed += 1
            stats["chunks"] += 1
        else:
            stats["errors"] += 1
    
    return indexed


async def main():
    print("🚀 Indexation de la documentation avec bge-m3")
    print("=" * 60)
    
    # Trouver tous les fichiers .md
    doc_path = Path(DOC_DIR)
    md_files = list(doc_path.rglob("*.md"))
    
    print(f"📁 Dossier: {DOC_DIR}")
    print(f"📄 Fichiers trouvés: {len(md_files)}")
    print()
    
    for filepath in sorted(md_files):
        stats["files"] += 1
        await process_file(filepath)
    
    print()
    print("=" * 60)
    print("📊 RÉSUMÉ")
    print(f"  - Fichiers traités: {stats['files']}")
    print(f"  - Chunks indexés: {stats['chunks']}")
    print(f"  - Fichiers ignorés: {stats['skipped']}")
    print(f"  - Erreurs: {stats['errors']}")
    print()
    print("✅ Indexation terminée!")


if __name__ == "__main__":
    asyncio.run(main())
