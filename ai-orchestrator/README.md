# 🧠 AI Orchestrator v4.0 (Secure Beta)

L'AI Orchestrator est un agent autonome avancé conçu pour gérer l'infrastructure de 4LB.ca. Il combine la puissance des LLMs (via Ollama) avec une exécution d'outils système sécurisée et une mémoire sémantique persistante.

## 🛡️ Sécurité & Architecture (Audit 2025)

Cette version a subi un audit de sécurité rigoureux.
- **Zéro `shell=True`** : Toutes les commandes système passent par une exécution directe sécurisée (`execve`), rendant les injections de commandes impossibles.
- **Whitelisting** : Seules les commandes et les chemins explicites sont autorisés.
- **Isolation** : L'architecture est modulaire (`backend/tools/`), séparant la logique métier de l'exécution.
- **Fail-Secure** : Le système refuse de démarrer si les modules de sécurité ne sont pas chargés.
- **Web Security** : Headers CSP stricts et sanitization des inputs (Docker names).

## 🚀 Fonctionnalités Clés

*   **Boucle ReAct** : Raisonnement "Think, Plan, Act" pour résoudre des tâches complexes.
*   **Mémoire Sémantique (RAG)** : Utilise ChromaDB pour se souvenir des projets, préférences et faits techniques entre les sessions.
*   **Outils Système** : Gestion Docker, analyse de fichiers, surveillance système (CPU/RAM/GPU).
*   **Multi-Modèles** : Support dynamique de Qwen 2.5 Coder, DeepSeek Coder et Llama Vision.
*   **Interface Réactive** : Frontend WebSocket temps réel avec affichage de la "pensée" de l'IA.

## 🛠️ Installation

### Prérequis
- Python 3.10+
- Ollama (avec les modèles `qwen2.5-coder:32b` et `nomic-embed-text`)
- ChromaDB (local ou docker)

### Configuration

1.  **Cloner le repo**
    ```bash
    git clone https://github.com/4lb/ai-orchestrator.git
    cd ai-orchestrator/backend
    ```

2.  **Environnement virtuel**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Variables d'environnement**
    Copiez `.env.example` vers `.env` et configurez :
    ```bash
    cp .env.example .env
    # Éditez .env pour définir JWT_SECRET_KEY et ADMIN_PASSWORD
    ```
    ⚠️ **IMPORTANT** : Le système ne démarrera pas si `JWT_SECRET_KEY` n'est pas sécurisé.

4.  **Démarrage**
    ```bash
    python main.py
    ```
    L'API sera accessible sur `http://localhost:8001`.

## 📚 Structure du Projet

```
backend/
├── main.py             # Point d'entrée API (FastAPI)
├── engine.py           # Moteur ReAct (Boucle de raisonnement)
├── security.py         # Validateurs de sécurité & Audit log
├── tools/              # Modules d'outils (Docker, File, System...)
├── utils/              # Utilitaires (Async subprocess sécurisé)
└── data/               # Base de données et Logs
frontend/
└── index.html          # Interface utilisateur (Single File Component)
```

## 🔍 Outils Disponibles

- **Système** : `execute_command`, `system_info`, `service_status`
- **Fichiers** : `read_file`, `write_file`, `search_files`
- **Docker** : `docker_status`, `docker_logs`, `docker_restart`
- **Mémoire** : `memory_store`, `memory_recall`

## 🤝 Contribution

Les contributions sont bienvenues. Toute modification touchant aux outils système doit passer par le validateur `security.py`.