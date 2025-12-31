#!/usr/bin/env python3
"""
Tests complets pour RAG Apogée v2.0
Exécuter: python3 -m services.rag.tests
"""

import asyncio
import sys
from datetime import datetime

# Configuration pour tests
import os
os.environ.setdefault("CHROMADB_HOST", "chromadb")
os.environ.setdefault("OLLAMA_URL", "http://10.10.10.46:11434")


async def test_config():
    """Test de la configuration"""
    print("\n📋 Test Configuration...")
    from services.rag.config import get_rag_config, RAGConfig
    
    config = get_rag_config()
    
    assert config.embedding_model == "bge-m3", f"Modèle incorrect: {config.embedding_model}"
    assert config.collection_name == "ai_orchestrator_memory_v3"
    assert config.chunk_size_tokens == 768
    assert config.embedding_dimensions == 1024
    
    print(f"  ✅ Modèle embedding: {config.embedding_model}")
    print(f"  ✅ Collection: {config.collection_name}")
    print(f"  ✅ Chunk size: {config.chunk_size_chars} chars")
    return True


async def test_embeddings():
    """Test du service d'embeddings"""
    print("\n🧠 Test Embeddings...")
    from services.rag.embeddings import get_embedding_service
    
    service = get_embedding_service()
    
    # Test 1: Génération simple
    result = await service.generate("Comment installer Docker sur Ubuntu?")
    assert result is not None, "Embedding None"
    assert len(result.embedding) == 1024, f"Dimension incorrecte: {len(result.embedding)}"
    assert result.model == "bge-m3"
    print(f"  ✅ Embedding généré: {len(result.embedding)} dims, {result.generation_time_ms:.0f}ms")
    
    # Test 2: Cache
    result2 = await service.generate("Comment installer Docker sur Ubuntu?")
    assert result2.cached == True, "Cache non utilisé"
    print(f"  ✅ Cache hit: {result2.generation_time_ms:.0f}ms")
    
    # Test 3: Stats
    stats = service.stats
    assert stats["total_generations"] >= 1
    print(f"  ✅ Stats: {stats['cache']['hit_rate']} hit rate")
    
    return True


async def test_search():
    """Test du service de recherche"""
    print("\n🔍 Test Recherche...")
    from services.rag.search import get_search_service
    
    service = get_search_service()
    
    # Test 1: Recherche simple
    response = await service.search("Comment configurer Traefik?", top_k=3)
    assert response is not None
    print(f"  ✅ Recherche: {len(response.results)} résultats en {response.search_time_ms:.0f}ms")
    
    if response.results:
        best = response.results[0]
        print(f"  ✅ Meilleur: [{best.filename}] {best.score:.0%}")
    
    # Test 2: Avec reranking
    response2 = await service.search("architecture serveur unified-stack", top_k=5, use_reranking=True)
    print(f"  ✅ Avec reranking: {len(response2.results)} résultats, rerank={response2.used_reranking}")
    
    # Test 3: Recherche vide
    response3 = await service.search("xyzabc123nonexistent", top_k=3)
    print(f"  ✅ Recherche vide gérée: {len(response3.results)} résultats")
    
    return True


async def test_context_injector():
    """Test de l'injecteur de contexte"""
    print("\n💉 Test Context Injector...")
    from services.rag.context_injector import get_context_injector
    
    injector = get_context_injector()
    
    # Test 1: Query pertinente
    result = await injector.get_context_for_query("Comment gérer la stack Docker unified?")
    print(f"  ✅ Contexte: {len(result.sources)} sources, score={result.relevance_score:.2f}")
    
    # Test 2: Query courte (pas d'injection)
    result2 = await injector.get_context_for_query("bonjour")
    assert result2.injected == False, "Injection sur salutation"
    print(f"  ✅ Salutation ignorée: injected={result2.injected}")
    
    # Test 3: Injection dans prompt
    system_prompt = "Tu es un assistant IA."
    enriched, result3 = await injector.inject_into_prompt(
        system_prompt, 
        "Comment fonctionne l'AI Orchestrator?"
    )
    if result3.injected:
        print(f"  ✅ Prompt enrichi: +{len(enriched) - len(system_prompt)} chars")
    else:
        print(f"  ⚠️ Pas de contexte pertinent trouvé")
    
    return True


async def test_reranker():
    """Test du service de reranking"""
    print("\n📊 Test Reranker...")
    from services.rag.reranker import get_reranker_service
    
    service = get_reranker_service()
    
    # Documents de test
    docs = [
        ("Docker est une plateforme de conteneurisation", {"topic": "docker"}, 0.5),
        ("Traefik est un reverse proxy moderne", {"topic": "traefik"}, 0.6),
        ("Python est un langage de programmation", {"topic": "code"}, 0.7),
    ]
    
    results, stats = await service.rerank("Comment configurer Docker?", docs, top_k=2)
    
    print(f"  ✅ Reranking: {stats.input_count} → {stats.output_count} docs")
    print(f"  ✅ Temps: {stats.rerank_time_ms:.0f}ms")
    
    if results:
        print(f"  ✅ Top result: {results[0].combined_score:.2%}")
    
    return True


async def test_full_pipeline():
    """Test du pipeline complet"""
    print("\n🚀 Test Pipeline Complet...")
    from services.rag import search_documents, inject_rag_context
    
    # Test 1: Recherche via fonction utilitaire
    response = await search_documents("Comment installer Continue.dev?", top_k=3)
    print(f"  ✅ search_documents: {len(response.results)} résultats")
    
    # Test 2: Injection via fonction utilitaire
    prompt = "Tu es un assistant pour gérer un serveur Ubuntu."
    enriched, result = await inject_rag_context(prompt, "Quelles sont les commandes pour gérer la stack?")
    
    if result.injected:
        print(f"  ✅ inject_rag_context: {len(result.sources)} sources injectées")
    else:
        print(f"  ⚠️ Pas de contexte trouvé (score min non atteint)")
    
    return True


async def run_all_tests():
    """Exécute tous les tests"""
    print("=" * 60)
    print("🧪 TESTS RAG APOGÉE v2.0")
    print("=" * 60)
    
    start = datetime.now()
    results = {}
    
    tests = [
        ("Configuration", test_config),
        ("Embeddings", test_embeddings),
        ("Search", test_search),
        ("Reranker", test_reranker),
        ("Context Injector", test_context_injector),
        ("Pipeline Complet", test_full_pipeline),
    ]
    
    for name, test_func in tests:
        try:
            success = await test_func()
            results[name] = "✅ PASS" if success else "❌ FAIL"
        except Exception as e:
            results[name] = f"❌ ERROR: {e}"
            print(f"  ❌ Exception: {e}")
    
    duration = (datetime.now() - start).total_seconds()
    
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 60)
    
    for name, status in results.items():
        print(f"  {name}: {status}")
    
    passed = sum(1 for s in results.values() if "PASS" in s)
    total = len(results)
    
    print(f"\n  Total: {passed}/{total} tests passés en {duration:.1f}s")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
