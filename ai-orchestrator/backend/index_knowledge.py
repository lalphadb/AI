#!/usr/bin/env python3
"""
Script d'indexation de la Knowledge Base pour AI Orchestrator
Peuple la memoire semantique avec le contexte de l'infrastructure

Usage:
    python index_knowledge.py
    docker exec ai-orchestrator-backend python index_knowledge.py
"""

import asyncio
import os
from datetime import datetime

import httpx

# Configuration
CHROMADB_HOST = os.getenv("CHROMADB_HOST", "chromadb")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8000"))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://10.10.10.46:11434")
EMBEDDING_MODEL = "mxbai-embed-large"
COLLECTION_NAME = "ai_orchestrator_memory_v2"

# === KNOWLEDGE BASE ===
KNOWLEDGE_BASE = [
    # Infrastructure
    {
        "key": "serveur_specs",
        "category": "infra",
        "value": "Serveur principal: Ubuntu 25.10 (questing), AMD Ryzen 9 7900X 12 cores/24 threads, 64GB DDR5 RAM, NVIDIA RTX 5070 Ti 16GB VRAM, 2x NVMe (2TB Kingston + 1TB ORICO)",
    },
    {
        "key": "gpu_config",
        "category": "infra",
        "value": "GPU NVIDIA GeForce RTX 5070 Ti avec 16GB VRAM, CUDA 13.0, Driver 580.105.08. Utilise pour inference LLM via Ollama et rendu graphique.",
    },
    {
        "key": "network_config",
        "category": "infra",
        "value": "Reseau 10.10.10.0/25, serveur IP 10.10.10.46, UniFi Dream Machine Pro comme routeur/firewall. VLANs configures pour segmentation.",
    },
    {
        "key": "storage_config",
        "category": "infra",
        "value": "Stockage: /dev/nvme1n1 (2TB) pour systeme et donnees, /dev/nvme0n1 (1TB) monte sur /mnt/ollama-models pour les modeles LLM. ~80GB de modeles actuellement.",
    },
    # Docker & Services
    {
        "key": "docker_stack",
        "category": "infra",
        "value": "unified-stack Docker Compose avec ~16 services: traefik (reverse proxy SSL), postgres, redis, chromadb, ollama, open-webui, grafana, prometheus, cadvisor, node-exporter, crowdsec, code-server, et sites web JSR",
    },
    {
        "key": "traefik_config",
        "category": "infra",
        "value": "Traefik v3.6 comme reverse proxy avec Let's Encrypt pour SSL automatique. Domaines: ai.4lb.ca, llm.4lb.ca, grafana.4lb.ca, jsr-dev.4lb.ca, jsr-solutions.ca",
    },
    {
        "key": "monitoring_stack",
        "category": "infra",
        "value": "Stack monitoring: Prometheus pour metriques, Grafana pour dashboards, cAdvisor pour conteneurs Docker, node-exporter pour metriques systeme, CrowdSec pour securite",
    },
    # LLM & AI
    {
        "key": "ollama_models",
        "category": "llm",
        "value": "Modeles Ollama installes: qwen2.5-coder:32b (code principal), deepseek-coder:33b (alternative), qwen3-vl:32b (vision), llama3.2-vision:11b (vision leger), nomic-embed-text (embeddings), mxbai-embed-large (embeddings v2)",
    },
    {
        "key": "ai_orchestrator",
        "category": "llm",
        "value": "AI Orchestrator: Agent autonome ReAct avec FastAPI, ChromaDB pour memoire semantique, support multi-modeles, outils systeme/docker/fichiers/memoire. Interface web sur ai.4lb.ca",
    },
    {
        "key": "chromadb_usage",
        "category": "llm",
        "value": "ChromaDB utilise pour memoire semantique vectorielle. Collection ai_orchestrator_memory_v2 avec embeddings mxbai-embed-large (1024 dimensions). Stocke contexte, conversations, faits.",
    },
    # Projets
    {
        "key": "projets_actifs",
        "category": "project",
        "value": "Projets actifs: AI Orchestrator (agent autonome), JSR Solutions (site excavation/deneigement), JSR Toilettage (site toilettage animaux), unified-stack (infrastructure Docker)",
    },
    {
        "key": "projet_jsr",
        "category": "project",
        "value": "JSR Solutions: Entreprise excavation et deneigement a Lac-Saint-Charles Quebec. Site web jsr-solutions.ca avec design moderne vert, conformite Loi 25 Quebec.",
    },
    {
        "key": "chemins_projets",
        "category": "project",
        "value": "Structure projets: /home/lalpha/projets/ contient ai-tools/, clients/, infrastructure/, web-apps/. AI Orchestrator dans /home/lalpha/projets/ai-tools/ai-orchestrator/",
    },
    # Preferences utilisateur
    {
        "key": "user_language",
        "category": "user",
        "value": "Utilisateur Lalpha prefere le francais pour les communications. Reponses techniques concises avec commandes exactes appreciees.",
    },
    {
        "key": "user_expertise",
        "category": "user",
        "value": "Lalpha est developpeur et sysadmin experimente. Connait Docker, Linux, Python, JavaScript, reseaux. Prefere solutions directes sans explications basiques.",
    },
    {
        "key": "user_workflow",
        "category": "user",
        "value": "Workflow prefere: commandes directes, scripts automatises, Docker pour isolation, Git pour versionning, monitoring proactif.",
    },
]


async def get_embedding(text: str) -> list:
    """Generer embedding via Ollama"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/embeddings", json={"model": EMBEDDING_MODEL, "prompt": text}
        )
        if response.status_code == 200:
            return response.json().get("embedding")
        else:
            raise Exception(f"Embedding error: {response.status_code}")


async def index_all():
    """Indexer toute la knowledge base"""
    import chromadb

    print(f"Connexion ChromaDB {CHROMADB_HOST}:{CHROMADB_PORT}...")
    client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)

    print(f"Creation/recuperation collection {COLLECTION_NAME}...")
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            "description": "Memoire semantique AI Orchestrator v2",
            "embedding_model": EMBEDDING_MODEL,
            "indexed_at": datetime.now().isoformat(),
        },
    )

    print(f"\nIndexation de {len(KNOWLEDGE_BASE)} documents...")

    for i, item in enumerate(KNOWLEDGE_BASE, 1):
        key = item["key"]
        category = item["category"]
        value = item["value"]

        # Generer ID unique
        doc_id = f"{category}_{key}".replace(" ", "_").lower()[:64]

        # Generer embedding
        print(f"  [{i}/{len(KNOWLEDGE_BASE)}] {key}...", end=" ")
        try:
            embedding = await get_embedding(f"{category}: {key} - {value}")

            # Upsert dans ChromaDB
            collection.upsert(
                ids=[doc_id],
                documents=[value],
                embeddings=[embedding],
                metadatas=[
                    {
                        "key": key,
                        "category": category,
                        "timestamp": datetime.now().isoformat(),
                        "source": "knowledge_base",
                        "embedding_model": EMBEDDING_MODEL,
                    }
                ],
            )
            print("OK")
        except Exception as e:
            print(f"ERREUR: {e}")

    # Stats finales
    count = collection.count()
    print("\nIndexation terminee!")
    print(f"Total documents dans {COLLECTION_NAME}: {count}")


if __name__ == "__main__":
    asyncio.run(index_all())
