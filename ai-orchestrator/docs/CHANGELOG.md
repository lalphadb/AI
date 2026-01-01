# 📋 Changelog - AI Orchestrator

Toutes les modifications notables de ce projet sont documentées dans ce fichier.

Format basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).

---

## [5.2.1] - 2026-01-01

### ✨ Ajouté
- **Gmail Integration** : 11 nouveaux outils pour gérer les emails
  - `gmail_search`, `gmail_list`, `gmail_read`
  - `gmail_send`, `gmail_reply`, `gmail_delete`
  - `gmail_label_list`, `gmail_label_create`, `gmail_label_apply`
  - `gmail_archive`, `gmail_stats`
- Mode **exécution autonome** : L'agent exécute les actions au lieu de recommander
- Rapport d'audit complet dans `.auto-claude/specs/003-corrections/AUDIT_REPORT.md`

### ✅ Sécurité (Audit Auto-Claude)
- Suppression `python-jose` (CVE-2024-33663, CVE-2024-33664)
- Upgrade `python-multipart` → 0.0.18 (CVE-2024-53981)
- Upgrade `FastAPI` → 0.115.6 (fix Starlette CVEs)
- Remplacement `datetime.utcnow()` → `datetime.now(timezone.utc)`
- Dockerfile : utilisateur non-root `appuser`
- Docker Compose : limites CPU/RAM ajoutées
- Configuration Ruff avec règles sécurité (S, C4, UP)

### 🔧 Amélioré
- Score Pylint : 8.20 → **9.68/10**
- Erreurs Ruff : 804 → **59** (auto-fix)
- Total outils : 57 → **70**
- pip-audit : **0 vulnérabilités**

---

## [5.2.0] - 2025-12-31

### ✨ Ajouté
- RAG Apogée v2.0 : Architecture professionnelle complète
- Mémoire sémantique persistante via ChromaDB
- Script d'indexation documentation
- Embeddings BGE-M3

### 🔧 Amélioré
- Refactoring complet des tools
- Meilleure gestion des erreurs

---

## [5.0.0] - 2025-12-15

### ✨ Ajouté
- Boucle ReAct (Reason-Act-Observe) avec 30 itérations max
- Auto-apprentissage et auto-amélioration
- Self-healing service
- 34+ outils initiaux
- Authentification JWT
- Rate limiting
- Support multi-modèles (local + cloud)

### 🏗 Infrastructure
- Intégration Docker Compose dans unified-stack
- Traefik reverse proxy avec SSL
- ChromaDB pour mémoire vectorielle

---

## [4.0.0] - 2025-11-01

### ✨ Ajouté
- Architecture modulaire avec chargement dynamique
- Support Ollama multi-modèles
- Interface WebSocket temps réel

---

## [3.0.0] - 2025-09-15

### ✨ Ajouté
- API REST FastAPI
- Authentification basique
- Outils système de base

---

## [2.0.0] - 2025-08-15

### ✨ Ajouté
- Prototype agent conversationnel
- Connexion Ollama basique

---

## [1.0.0] - 2025-08-01

### ✨ Ajouté
- Concept initial
- Proof of concept

---

## Légende

| Icône | Description |
|-------|-------------|
| ✨ | Nouvelle fonctionnalité |
| 🔧 | Amélioration |
| 🐛 | Correction de bug |
| 🏗 | Infrastructure |
| ✅ | Sécurité |
| ⚠️ | Déprécié |
| ❌ | Supprimé |

---

*Changelog - AI Orchestrator v5.2.1*
