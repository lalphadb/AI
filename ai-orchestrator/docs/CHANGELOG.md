# 📋 Changelog - AI Orchestrator

Toutes les modifications notables de ce projet sont documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/).

---

## [5.2] - 2025-12-31

### Sécurité
- ✅ Régénération complète des secrets (.env)
- ✅ Correction injection SSH via `shlex.quote()`
- ✅ Désactivation `create_tool` en production
- ✅ Suppression accès anonyme admin
- ✅ Réduction expiration JWT à 1 heure
- ✅ Extension blacklist à 30+ commandes
- ✅ Ajout validation symlink bypass

### Amélioré
- 🔧 Audit de sécurité complet (méthodologie OWASP)
- 🔧 Documentation professionnelle restructurée
- 🔧 Nettoyage fichiers obsolètes

### En cours
- ⚠️ Migration docker-socket-proxy
- ⚠️ Restriction volumes /home
- ⚠️ Configuration bouncer CrowdSec

---

## [5.1] - 2025-12-29

### Ajouté
- ✨ Mode autonome avec approche blacklist
- ✨ Router intelligent (factuel/opérationnel)
- ✨ Injection de contexte dynamique
- ✨ Self-healing system
- ✨ Support multi-modèles cloud (Kimi, Gemini, Qwen Cloud)

### Amélioré
- 🔧 Boucle ReAct optimisée (max 15 itérations)
- 🔧 Collecte des résultats pour réponse finale
- 🔧 Streaming WebSocket amélioré
- 🔧 Rate limiting par endpoint

### Corrigé
- 🐛 Fix réponses vides (P0-1)
- 🐛 Fix collecte résultats outils (P0-2)
- 🐛 Fix logs THINK/ACTION/OBSERVE (P0-3)

---

## [5.0] - 2025-12-15

### Ajouté
- ✨ Architecture complète ReAct (Reason-Act-Observe)
- ✨ 57 outils intégrés (9 catégories)
- ✨ Mémoire sémantique ChromaDB
- ✨ Authentification JWT + API Keys
- ✨ Interface web temps réel (WebSocket)
- ✨ Support vision (Llama Vision, Qwen VL)

### Infrastructure
- 🏗 Migration vers unified-stack
- 🏗 Intégration Traefik v3
- 🏗 Monitoring Prometheus/Grafana
- 🏗 CrowdSec IPS

---

## [4.0] - 2025-11-20

### Ajouté
- ✨ Auto-apprentissage des conversations
- ✨ Outils Docker complets
- ✨ Outils Git intégrés
- ✨ Gestion des fichiers

### Amélioré
- 🔧 Performance LLM (caching)
- 🔧 Gestion erreurs robuste

---

## [3.0] - 2025-10-15

### Ajouté
- ✨ Backend FastAPI
- ✨ Frontend HTML/TailwindCSS
- ✨ Intégration Ollama
- ✨ Premiers outils système

### Infrastructure
- 🏗 Docker Compose initial
- 🏗 SQLite pour persistance

---

## [2.0] - 2025-09-01

### Ajouté
- ✨ Prototype agent conversationnel
- ✨ Connexion Ollama basique

---

## [1.0] - 2025-08-01

### Ajouté
- ✨ Concept initial
- ✨ Proof of concept

---

## Légende

| Icône | Description |
|-------|-------------|
| ✨ | Nouvelle fonctionnalité |
| 🔧 | Amélioration |
| 🐛 | Correction de bug |
| 🏗 | Infrastructure |
| ✅ | Sécurité |
| ⚠️ | En cours |
| ❌ | Supprimé |

---

*Changelog - AI Orchestrator*
