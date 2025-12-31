#!/usr/bin/env python3
"""
Service Reranker pour RAG Apogée
Utilise bge-reranker-v2-m3 via Ollama pour filtrer les résultats
"""

import httpx
import asyncio
from typing import List, Dict, Tuple, Optional
import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://10.10.10.46:11434")
RERANKER_MODEL = "qllama/bge-reranker-v2-m3"

# Cache pour éviter les appels répétés
_reranker_cache: Dict[str, float] = {}


async def get_rerank_score(query: str, document: str) -> float:
    """
    Obtient un score de pertinence entre une requête et un document.
    Le reranker retourne un embedding, on utilise la moyenne comme score.
    
    Note: bge-reranker est un cross-encoder, mais via Ollama on l'utilise
    différemment - on combine query+doc pour l'embedding.
    """
    cache_key = f"{hash(query)}:{hash(document)}"
    if cache_key in _reranker_cache:
        return _reranker_cache[cache_key]
    
    # Format cross-encoder: query [SEP] document
    combined_text = f"Query: {query}\nDocument: {document}"
    
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": RERANKER_MODEL, "prompt": combined_text}
            )
            
            if response.status_code == 200:
                data = response.json()
                embedding = data.get("embedding", [])
                if embedding:
                    # Score basé sur la magnitude de l'embedding
                    # Plus le reranker "comprend" la relation, plus le score est élevé
                    score = sum(abs(x) for x in embedding[:100]) / 100
                    _reranker_cache[cache_key] = score
                    return score
    except Exception as e:
        print(f"⚠️ Erreur reranker: {e}")
    
    return 0.0


async def rerank_documents(
    query: str, 
    documents: List[Dict], 
    top_k: int = 5,
    score_threshold: float = 0.0
) -> List[Dict]:
    """
    Rerank une liste de documents par pertinence.
    
    Args:
        query: La requête utilisateur
        documents: Liste de dicts avec au moins 'content' ou 'text'
        top_k: Nombre de documents à retourner
        score_threshold: Score minimum pour inclure un document
        
    Returns:
        Liste des top_k documents triés par pertinence
    """
    if not documents:
        return []
    
    # Extraire le texte de chaque document
    scored_docs = []
    
    # Paralléliser les appels au reranker
    tasks = []
    for doc in documents:
        text = doc.get("content") or doc.get("text") or doc.get("document", "")
        if text:
            tasks.append(get_rerank_score(query, text[:2000]))  # Limiter la taille
    
    scores = await asyncio.gather(*tasks)
    
    for doc, score in zip(documents, scores):
        if score >= score_threshold:
            doc_copy = doc.copy()
            doc_copy["rerank_score"] = score
            scored_docs.append(doc_copy)
    
    # Trier par score décroissant
    scored_docs.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
    
    return scored_docs[:top_k]


async def hybrid_search_with_rerank(
    query: str,
    dense_results: List[Dict],
    sparse_results: Optional[List[Dict]] = None,
    top_k: int = 5
) -> List[Dict]:
    """
    Combine recherche dense et sparse, puis rerank.
    
    Args:
        query: Requête utilisateur
        dense_results: Résultats de la recherche vectorielle
        sparse_results: Résultats de la recherche par mots-clés (optionnel)
        top_k: Nombre final de résultats
        
    Returns:
        Documents rerankés
    """
    # Fusionner les résultats (déduplication par contenu)
    seen_contents = set()
    combined = []
    
    for doc in dense_results:
        content = doc.get("content") or doc.get("text", "")
        content_hash = hash(content[:500])
        if content_hash not in seen_contents:
            seen_contents.add(content_hash)
            doc["source"] = "dense"
            combined.append(doc)
    
    if sparse_results:
        for doc in sparse_results:
            content = doc.get("content") or doc.get("text", "")
            content_hash = hash(content[:500])
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                doc["source"] = "sparse"
                combined.append(doc)
    
    # Rerank le tout
    return await rerank_documents(query, combined, top_k=top_k)


def clear_cache():
    """Vide le cache du reranker"""
    global _reranker_cache
    _reranker_cache = {}


# Test standalone
if __name__ == "__main__":
    async def test():
        query = "Comment configurer Docker sur Ubuntu?"
        docs = [
            {"content": "Docker est un outil de conteneurisation. Pour l'installer sur Ubuntu, utilisez apt-get install docker.io"},
            {"content": "Python est un langage de programmation populaire pour le machine learning."},
            {"content": "La configuration Docker nécessite d'ajouter votre utilisateur au groupe docker avec usermod -aG docker $USER"},
        ]
        
        results = await rerank_documents(query, docs, top_k=2)
        print("Résultats rerankés:")
        for i, doc in enumerate(results, 1):
            print(f"{i}. Score: {doc['rerank_score']:.3f} - {doc['content'][:80]}...")
    
    asyncio.run(test())
