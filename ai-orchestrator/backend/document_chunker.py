#!/usr/bin/env python3
"""
Document Chunker pour AI Orchestrator
Decoupe les documents longs en chunks semantiques avec overlap
Optimise pour embeddings mxbai-embed-large (1024 dim, ~512 tokens max)
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Chunk:
    """Represente un chunk de document"""

    content: str
    index: int
    start_char: int
    end_char: int
    metadata: Dict


# Configuration chunking
DEFAULT_CHUNK_SIZE = 500  # tokens approximatifs (~2000 chars)
DEFAULT_OVERLAP = 50  # tokens overlap (~200 chars)
CHARS_PER_TOKEN = 4  # estimation moyenne francais


def count_tokens_approx(text: str) -> int:
    """Estimation du nombre de tokens (approximatif)"""
    return len(text) // CHARS_PER_TOKEN


def split_into_sentences(text: str) -> List[str]:
    """Decouper texte en phrases"""
    # Pattern pour fin de phrase (., !, ?, :) suivi d'espace ou fin
    pattern = r"(?<=[.!?:])\s+"
    sentences = re.split(pattern, text)
    return [s.strip() for s in sentences if s.strip()]


def split_into_paragraphs(text: str) -> List[str]:
    """Decouper texte en paragraphes"""
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    respect_sentences: bool = True,
) -> List[Chunk]:
    """
    Decouper un texte en chunks avec overlap

    Args:
        text: Texte a decouper
        chunk_size: Taille cible en tokens (~4 chars/token)
        overlap: Nombre de tokens de chevauchement
        respect_sentences: Essayer de couper sur les fins de phrases

    Returns:
        Liste de Chunks
    """
    if not text or not text.strip():
        return []

    text = text.strip()

    # Si le texte est assez court, un seul chunk
    if count_tokens_approx(text) <= chunk_size:
        return [
            Chunk(
                content=text,
                index=0,
                start_char=0,
                end_char=len(text),
                metadata={"is_single": True, "total_chunks": 1},
            )
        ]

    chunks = []
    chunk_chars = chunk_size * CHARS_PER_TOKEN
    overlap_chars = overlap * CHARS_PER_TOKEN

    if respect_sentences:
        # Methode intelligente: respecter les phrases
        sentences = split_into_sentences(text)

        current_chunk = []
        current_length = 0
        chunk_start = 0
        char_pos = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            # Si ajouter cette phrase depasse la limite
            if current_length + sentence_len > chunk_chars and current_chunk:
                # Sauvegarder le chunk actuel
                chunk_text_content = " ".join(current_chunk)
                chunks.append(
                    Chunk(
                        content=chunk_text_content,
                        index=len(chunks),
                        start_char=chunk_start,
                        end_char=char_pos,
                        metadata={},
                    )
                )

                # Overlap: garder les dernieres phrases pour le prochain chunk
                overlap_content = []
                overlap_len = 0
                for s in reversed(current_chunk):
                    if overlap_len + len(s) <= overlap_chars:
                        overlap_content.insert(0, s)
                        overlap_len += len(s)
                    else:
                        break

                current_chunk = overlap_content
                current_length = overlap_len
                chunk_start = char_pos - overlap_len

            current_chunk.append(sentence)
            current_length += sentence_len
            char_pos += sentence_len + 1  # +1 pour l'espace

        # Dernier chunk
        if current_chunk:
            chunk_text_content = " ".join(current_chunk)
            chunks.append(
                Chunk(
                    content=chunk_text_content,
                    index=len(chunks),
                    start_char=chunk_start,
                    end_char=len(text),
                    metadata={},
                )
            )
    else:
        # Methode simple: decoupage fixe
        start = 0
        while start < len(text):
            end = min(start + chunk_chars, len(text))

            # Essayer de couper sur un espace
            if end < len(text):
                space_pos = text.rfind(" ", start, end)
                if space_pos > start + chunk_chars // 2:
                    end = space_pos

            chunk_content = text[start:end].strip()
            if chunk_content:
                chunks.append(
                    Chunk(
                        content=chunk_content,
                        index=len(chunks),
                        start_char=start,
                        end_char=end,
                        metadata={},
                    )
                )

            # Avancer start, eviter boucle infinie
            if end >= len(text):
                break  # Fin du texte atteinte
            new_start = end - overlap_chars
            if new_start <= start:
                new_start = end  # Forcer l'avancement
            start = max(0, new_start)

    # Mettre a jour metadata avec total_chunks
    total = len(chunks)
    for chunk in chunks:
        chunk.metadata.update({"is_single": total == 1, "total_chunks": total})

    return chunks


def chunk_file_content(
    content: str,
    filename: str,
    file_type: str = "text",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> List[Dict]:
    """
    Chunker le contenu d'un fichier avec metadata enrichies

    Args:
        content: Contenu du fichier
        filename: Nom du fichier
        file_type: Type (text, code, markdown, config)
        chunk_size: Taille cible en tokens
        overlap: Overlap en tokens

    Returns:
        Liste de dicts prets pour indexation ChromaDB
    """
    # Adapter le chunking selon le type
    if file_type == "code":
        # Pour le code, decouper sur les fonctions/classes si possible
        chunks = chunk_code(content, chunk_size, overlap)
    elif file_type == "markdown":
        # Pour markdown, respecter les sections
        chunks = chunk_markdown(content, chunk_size, overlap)
    else:
        chunks = chunk_text(content, chunk_size, overlap)

    results = []
    for chunk in chunks:
        chunk_id = f"file_{filename.replace('/', '_').replace('.', '_')}_{chunk.index}"

        results.append(
            {
                "id": chunk_id[:64],  # ChromaDB limite 64 chars
                "content": chunk.content,
                "metadata": {
                    "source": "file",
                    "filename": filename,
                    "file_type": file_type,
                    "chunk_index": chunk.index,
                    "total_chunks": chunk.metadata.get("total_chunks", 1),
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                },
            }
        )

    return results


def chunk_code(content: str, chunk_size: int, overlap: int) -> List[Chunk]:
    """Chunker du code en respectant les blocs (fonctions, classes)"""
    # Pattern pour detecter les debuts de fonctions/classes Python
    block_pattern = r"^(def |class |async def )"

    lines = content.split("\n")
    blocks = []
    current_block = []
    current_start = 0
    char_pos = 0

    for i, line in enumerate(lines):
        if re.match(block_pattern, line.strip()) and current_block:
            # Nouveau bloc, sauvegarder l'ancien
            blocks.append(
                {"content": "\n".join(current_block), "start": current_start, "end": char_pos}
            )
            current_block = []
            current_start = char_pos

        current_block.append(line)
        char_pos += len(line) + 1

    # Dernier bloc
    if current_block:
        blocks.append(
            {"content": "\n".join(current_block), "start": current_start, "end": char_pos}
        )

    # Convertir blocs en chunks (fusionner si trop petits, decouper si trop grands)
    chunks = []
    current_chunk_content = ""
    current_chunk_start = 0

    for block in blocks:
        block_tokens = count_tokens_approx(block["content"])
        current_tokens = count_tokens_approx(current_chunk_content)

        if current_tokens + block_tokens <= chunk_size:
            # Fusionner
            if current_chunk_content:
                current_chunk_content += "\n\n"
            current_chunk_content += block["content"]
        else:
            # Sauvegarder et commencer nouveau chunk
            if current_chunk_content:
                chunks.append(
                    Chunk(
                        content=current_chunk_content,
                        index=len(chunks),
                        start_char=current_chunk_start,
                        end_char=block["start"],
                        metadata={"type": "code"},
                    )
                )

            # Si le bloc est trop grand, le decouper
            if block_tokens > chunk_size:
                sub_chunks = chunk_text(
                    block["content"], chunk_size, overlap, respect_sentences=False
                )
                for sc in sub_chunks:
                    sc.index = len(chunks)
                    sc.metadata["type"] = "code"
                    chunks.append(sc)
                current_chunk_content = ""
                current_chunk_start = block["end"]
            else:
                current_chunk_content = block["content"]
                current_chunk_start = block["start"]

    # Dernier chunk
    if current_chunk_content:
        chunks.append(
            Chunk(
                content=current_chunk_content,
                index=len(chunks),
                start_char=current_chunk_start,
                end_char=len(content),
                metadata={"type": "code"},
            )
        )

    # Mise a jour indices et metadata
    for i, chunk in enumerate(chunks):
        chunk.index = i
        chunk.metadata["total_chunks"] = len(chunks)
        chunk.metadata["is_single"] = len(chunks) == 1

    return chunks


def chunk_markdown(content: str, chunk_size: int, overlap: int) -> List[Chunk]:
    """Chunker du markdown en respectant les sections (headers)"""
    # Pattern pour headers markdown
    header_pattern = r"^(#{1,6})\s+(.+)$"

    lines = content.split("\n")
    sections = []
    current_section = {"header": "", "content": [], "start": 0}
    char_pos = 0

    for line in lines:
        header_match = re.match(header_pattern, line.strip())
        if header_match and current_section["content"]:
            # Nouvelle section
            current_section["end"] = char_pos
            sections.append(current_section)
            current_section = {"header": line.strip(), "content": [line], "start": char_pos}
        else:
            current_section["content"].append(line)

        char_pos += len(line) + 1

    # Derniere section
    current_section["end"] = char_pos
    sections.append(current_section)

    # Convertir sections en chunks
    chunks = []
    for section in sections:
        section_content = "\n".join(section["content"])
        section_tokens = count_tokens_approx(section_content)

        if section_tokens <= chunk_size:
            chunks.append(
                Chunk(
                    content=section_content,
                    index=len(chunks),
                    start_char=section["start"],
                    end_char=section["end"],
                    metadata={"type": "markdown", "header": section["header"]},
                )
            )
        else:
            # Decouper la section
            sub_chunks = chunk_text(section_content, chunk_size, overlap)
            for sc in sub_chunks:
                sc.index = len(chunks)
                sc.start_char += section["start"]
                sc.end_char += section["start"]
                sc.metadata["type"] = "markdown"
                sc.metadata["header"] = section["header"]
                chunks.append(sc)

    # Mise a jour metadata
    for i, chunk in enumerate(chunks):
        chunk.index = i
        chunk.metadata["total_chunks"] = len(chunks)
        chunk.metadata["is_single"] = len(chunks) == 1

    return chunks


if __name__ == "__main__":
    # Test
    test_text = """
    Ceci est un premier paragraphe avec plusieurs phrases. Il contient des informations importantes.
    Voici une autre phrase pour tester.

    Deuxieme paragraphe ici. Encore plus de contenu pour voir comment le chunking fonctionne.
    Le systeme doit respecter les limites de phrases autant que possible.

    Troisieme paragraphe avec du contenu technique. Docker, Kubernetes, et autres technologies.
    Les embeddings doivent capturer le sens semantique de chaque chunk.
    """

    chunks = chunk_text(test_text, chunk_size=50, overlap=10)
    print(f"Texte original: {count_tokens_approx(test_text)} tokens")
    print(f"Nombre de chunks: {len(chunks)}")
    for chunk in chunks:
        print(f"\n--- Chunk {chunk.index} ({count_tokens_approx(chunk.content)} tokens) ---")
        print(chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content)
