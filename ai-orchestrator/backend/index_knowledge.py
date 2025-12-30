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
    # ============ INFRASTRUCTURE SERVEUR ============
    {
        "key": "serveur_specs",
        "category": "infra",
        "value": "Serveur principal lalpha-server-1: Ubuntu 25.10 (Questing), Kernel 6.17.0, AMD Ryzen 9 7900X 12 cores/24 threads, 64GB DDR5 RAM, NVIDIA RTX 5070 Ti 16GB VRAM, 2x NVMe (2TB Kingston systeme + 1TB ORICO modeles LLM)",
    },
    {
        "key": "gpu_config",
        "category": "infra",
        "value": "GPU NVIDIA GeForce RTX 5070 Ti avec 16GB VRAM, CUDA 12.4, Driver 580.105.08. Utilise pour inference LLM via Ollama (15.4GB disponible). Commandes: nvidia-smi, nvtop pour monitoring.",
    },
    {
        "key": "network_config",
        "category": "infra",
        "value": "Reseau 10.10.10.0/25, serveur IP 10.10.10.46, gateway UniFi Dream Machine Pro. VLANs segmentes. DNS local via Pi-hole optionnel.",
    },
    {
        "key": "storage_config",
        "category": "infra",
        "value": "Stockage: /dev/nvme1n1 (2TB Kingston) pour systeme et donnees (~300GB utilises, 18%). /dev/nvme0n1 (1TB ORICO) monte sur /mnt/ollama-models pour modeles LLM (~80GB modeles).",
    },
    {
        "key": "system_resources",
        "category": "infra",
        "value": "Utilisation normale: RAM ~14GB/64GB, Swap 8GB. Commandes diagnostic: htop, free -h, df -h, lsblk, sensors (temperatures).",
    },
    # ============ DOCKER INFRASTRUCTURE ============
    {
        "key": "docker_networks",
        "category": "docker",
        "value": "Reseaux Docker: unified-net (principal services), traefik-net (reverse proxy), 4lbca_frontend, 4lbca_backend, 4lbca_llm, 4lbca_monitoring. Tous externes et interconnectes via Traefik.",
    },
    {
        "key": "docker_stack",
        "category": "docker",
        "value": "unified-stack dans /home/lalpha/projets/infrastructure/unified-stack/ avec 16+ services. Commandes: docker compose up -d, docker compose logs -f [service], docker ps.",
    },
    {
        "key": "docker_volumes",
        "category": "docker",
        "value": "Volumes Docker persistants: traefik_certs, traefik_logs, postgres_data, redis_data, grafana_data, prometheus_data, open_webui_data, ai_orchestrator_data, chromadb_data, code_server_data, crowdsec_data.",
    },
    # ============ TRAEFIK & ROUTAGE ============
    {
        "key": "traefik_config",
        "category": "docker",
        "value": "Traefik v3.6 reverse proxy. Ports: 80 (redirect HTTPS), 443 (SSL), 8080 (dashboard). Let's Encrypt automatique via HTTP challenge. Config dynamique dans /configs/traefik/dynamic/.",
    },
    {
        "key": "traefik_routes",
        "category": "docker",
        "value": "Routes Traefik: ai.4lb.ca (AI Orchestrator), llm.4lb.ca (Open WebUI), grafana.4lb.ca (monitoring), traefik.4lb.ca (dashboard), jsr-solutions.ca (client JSR), jsr-dev.4lb.ca (dev JSR).",
    },
    {
        "key": "traefik_middlewares",
        "category": "docker",
        "value": "Middlewares Traefik: security-headers (CSP, HSTS), geoblock (filtrage geo IP), crowdsec-bouncer (protection attaques). Plugins: crowdsec-bouncer-traefik-plugin v1.4.4, traefik-geoblock v1.1.1.",
    },
    # ============ BASES DE DONNEES ============
    {
        "key": "postgres_config",
        "category": "docker",
        "value": "PostgreSQL 16-alpine, container postgres. DB principale: main, user: lalpha. Healthcheck: pg_isready. Backup: pg_dump. Reseau: unified-net.",
    },
    {
        "key": "redis_config",
        "category": "docker",
        "value": "Redis 7-alpine avec persistence AOF (appendonly yes). Container redis. Utilise pour cache, sessions, rate limiting. Commande test: redis-cli ping.",
    },
    {
        "key": "chromadb_config",
        "category": "docker",
        "value": "ChromaDB pour stockage vectoriel. Port 8000 interne, accessible via chromadb.4lb.ca. Collection principale: ai_orchestrator_memory_v2. API: /api/v2/collections.",
    },
    # ============ LLM & IA ============
    {
        "key": "ollama_service",
        "category": "llm",
        "value": "Ollama service systeme sur port 11434 (http://10.10.10.46:11434). Modeles stockes sur /mnt/ollama-models. Commandes: ollama list, ollama run [model], ollama pull [model].",
    },
    {
        "key": "ollama_models_local",
        "category": "llm",
        "value": "Modeles locaux Ollama: qwen2.5-coder:32b-instruct-q4_K_M (19GB, code principal), deepseek-coder:33b (18GB, alternative), llama3.2-vision:11b-instruct-q8_0 (12GB, vision), qwen3-vl:32b (20GB, multimodal).",
    },
    {
        "key": "ollama_models_cloud",
        "category": "llm",
        "value": "Modeles cloud Ollama (gratuits): qwen3-coder:480b-cloud (code avance), kimi-k2:1t-cloud (Moonshot), gemini-3-pro-preview (Google). Limites rate possibles.",
    },
    {
        "key": "ollama_embeddings",
        "category": "llm",
        "value": "Modeles embeddings: mxbai-embed-large (669MB, 1024 dim, multilingue, ACTIF), nomic-embed-text (274MB, 768 dim, legacy). mxbai recommande pour francais et code.",
    },
    {
        "key": "ai_orchestrator",
        "category": "llm",
        "value": "AI Orchestrator: agent ReAct autonome. Backend FastAPI port 8001, frontend nginx. 55 outils (docker, fichiers, systeme, memoire, git, reseau). Interface: ai.4lb.ca. Code: /home/lalpha/projets/ai-tools/ai-orchestrator/",
    },
    {
        "key": "ai_orchestrator_arch",
        "category": "llm",
        "value": "Architecture AI Orchestrator: engine.py (boucle ReAct THINK-PLAN-ACTION-OBSERVE), prompts.py (system prompts + router), tools/ (9 modules outils), ChromaDB (memoire), auto_learn.py (apprentissage auto).",
    },
    {
        "key": "open_webui",
        "category": "llm",
        "value": "Open WebUI sur llm.4lb.ca. Interface chat pour Ollama. Container open-webui. Supporte RAG, documents, historique conversations. Alternative interface a AI Orchestrator.",
    },
    # ============ MONITORING & SECURITE ============
    {
        "key": "monitoring_stack",
        "category": "monitoring",
        "value": "Stack monitoring: Prometheus (metriques, port 9090), Grafana (dashboards, grafana.4lb.ca), cAdvisor (conteneurs Docker), node-exporter (metriques systeme Linux).",
    },
    {
        "key": "grafana_config",
        "category": "monitoring",
        "value": "Grafana accessible sur grafana.4lb.ca. Dashboards: Docker containers, Node metrics, Traefik stats. Datasources: Prometheus. Alerting configure.",
    },
    {
        "key": "crowdsec_config",
        "category": "security",
        "value": "CrowdSec pour protection attaques. Collections: traefik, http-cve, whitelist-good-actors, iptables, linux. Analyse logs Traefik. Commande: cscli decisions list, cscli alerts list.",
    },
    {
        "key": "security_practices",
        "category": "security",
        "value": "Securite: HTTPS force partout, headers securite (CSP, HSTS), geoblock pays risques, CrowdSec IDS/IPS, secrets dans .env (jamais git), Docker networks isoles.",
    },
    # ============ PROJETS ============
    {
        "key": "projets_structure",
        "category": "project",
        "value": "Structure /home/lalpha/projets/: ai-tools/ (AI Orchestrator, MCP servers), clients/ (JSR, toilettage), infrastructure/ (unified-stack, configs), web-apps/ (sites perso), developpement/ (tests).",
    },
    {
        "key": "projet_ai_orchestrator",
        "category": "project",
        "value": "AI Orchestrator: /home/lalpha/projets/ai-tools/ai-orchestrator/. Backend Python FastAPI, Frontend HTML/JS. Docker Compose avec backend + frontend nginx. Git: github.com/...",
    },
    {
        "key": "projet_jsr_solutions",
        "category": "project",
        "value": "JSR Solutions: entreprise excavation/deneigement Lac-Saint-Charles Quebec. Site jsr-solutions.ca. Code: /home/lalpha/projets/clients/jsr/JSR-solutions/. Design vert moderne, Loi 25 conforme.",
    },
    {
        "key": "projet_jsr_toilettage",
        "category": "project",
        "value": "JSR Toilettage: site toilettage animaux. Plusieurs versions dans /home/lalpha/projets/clients/toilettage/versions/ (v1-backend-separe, v2-react-moderne, v3-monitoring-complet).",
    },
    {
        "key": "projet_unified_stack",
        "category": "project",
        "value": "unified-stack: infrastructure Docker principale. /home/lalpha/projets/infrastructure/unified-stack/. Docker Compose orchestrant tous les services (Traefik, DBs, monitoring, apps).",
    },
    # ============ OUTILS & SCRIPTS ============
    {
        "key": "backup_system",
        "category": "tools",
        "value": "Systeme backup dans /home/lalpha/projets/ai-tools/backup-system/. Backups quotidiens automatiques via cron. Cibles: ai-orchestrator, postgres, configs. Logs dans cron.log.",
    },
    {
        "key": "self_improvement",
        "category": "tools",
        "value": "Self-improvement reports dans /home/lalpha/projets/ai-tools/self-improvement/. Rapports automatiques analyse performance. Historique dans reports/history.json.",
    },
    {
        "key": "code_server",
        "category": "tools",
        "value": "code-server (VS Code web) disponible. Container code-server. Acces via Traefik. Utile pour edition code a distance.",
    },
    # ============ COMMANDES UTILES ============
    {
        "key": "cmd_docker",
        "category": "commands",
        "value": "Commandes Docker frequentes: docker ps, docker logs -f [container], docker compose up -d, docker compose build [service], docker exec -it [container] bash, docker stats.",
    },
    {
        "key": "cmd_debug",
        "category": "commands",
        "value": "Debug AI Orchestrator: docker logs ai-orchestrator-backend -f, curl localhost:8001/health, curl localhost:8001/api/stats. Rebuild: docker compose build backend && docker compose up -d backend.",
    },
    {
        "key": "cmd_ollama",
        "category": "commands",
        "value": "Commandes Ollama: ollama list (modeles), ollama run qwen2.5-coder:32b (chat), ollama pull mxbai-embed-large (telecharger), curl http://10.10.10.46:11434/api/tags (API liste).",
    },
    # ============ PREFERENCES UTILISATEUR ============
    {
        "key": "user_language",
        "category": "user",
        "value": "Utilisateur Lalpha prefere le francais pour communications. Reponses techniques concises avec commandes exactes. Pas d'explications basiques inutiles.",
    },
    {
        "key": "user_expertise",
        "category": "user",
        "value": "Lalpha: developpeur senior et sysadmin experimente. Maitrise Docker, Linux, Python, JavaScript, TypeScript, reseaux, securite. Prefere solutions directes et efficaces.",
    },
    {
        "key": "user_workflow",
        "category": "user",
        "value": "Workflow Lalpha: commandes directes, scripts automatises, Docker pour isolation, Git pour versionning, CI/CD, monitoring proactif, documentation minimale mais precise.",
    },
    {
        "key": "user_tools",
        "category": "user",
        "value": "Outils preferes: VS Code (local + code-server), terminal ZSH, Git, Docker Compose, Python 3.11+, Node.js, Claude Code pour dev assiste.",
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
