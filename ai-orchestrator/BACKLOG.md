# 📋 AI Orchestrator - Backlog

> **Version actuelle** : 2.3.0
> **Dernière mise à jour** : 9 décembre 2025

---

## ✅ Complété (v2.3.0)

### Phase 1 : Planification (v2.2)
- [x] `create_plan(task)` - Décomposition de tâches complexes
- [x] `validate_step(step, expected)` - Validation des étapes
- [x] Auto-correction avec détection d'erreurs
- [x] System prompt amélioré

### Phase 2 : RAG & Templates (v2.3)
- [x] `search_knowledge(query, collection)` - Recherche sémantique ChromaDB
- [x] `index_directory(path, collection)` - Indexation de répertoires
- [x] `create_project(type, name)` - Création de projets avec templates
- [x] `get_project_context(path)` - Analyse de contexte projet

---

## 🔴 P1 - Haute Priorité

### Git Avancé
- [ ] `git_commit(path, message)` - Commiter les changements
- [ ] `git_diff(path)` - Voir les différences
- [ ] `git_branch(path, action, name)` - Gérer les branches
- [ ] `git_log(path, n)` - Historique des commits

### Validation Code
- [ ] `run_tests(path, framework)` - pytest, npm test, jest
- [ ] `lint_code(path, language)` - Ruff, ESLint
- [ ] `format_code(path)` - Black, Prettier

---

## 🟠 P2 - Moyenne Priorité

### Gestion Dépendances
- [ ] `install_package(manager, package)` - pip, npm, apt
- [ ] `check_dependencies(path)` - Audit dépendances
- [ ] `update_dependencies(path)` - Mises à jour

### Outils Base de Données
- [ ] `db_query(database, query)` - Requêtes SQL
- [ ] `db_schema(database)` - Schéma de la DB
- [ ] `db_backup(database, path)` - Sauvegardes

### Amélioration UI
- [ ] Affichage du plan en temps réel
- [ ] Barre de progression des étapes
- [ ] Diff viewer pour fichiers modifiés
- [ ] Bouton d'annulation

---

## 🟢 P3 - Basse Priorité

### Agents Spécialisés
- [ ] `spawn_agent(type, task)` - Code, DevOps, Research agents

### Intégrations Externes
- [ ] Notifications Slack/Discord
- [ ] Création d'issues GitHub
- [ ] Webhooks personnalisés
- [ ] Rapports PDF

### Apprentissage
- [ ] Feedback utilisateur
- [ ] Apprentissage des erreurs
- [ ] Suggestions contextuelles

---

## 📊 Métriques

| Métrique | v2.0 | v2.2 | v2.3 | Cible |
|----------|------|------|------|-------|
| **Outils** | 26 | 28 | 32 | 40+ |
| **Lignes de code** | 1170 | 1309 | 1908 | - |
| **Tâches simples** | ~80% | ~85% | ~85% | 95% |
| **Tâches complexes** | ~40% | ~60% | ~70% | 85% |

---

## 🧪 Tests Recommandés

### Test RAG
```
1. "Indexe ma documentation: /home/lalpha/documentation"
2. "Cherche comment configurer Traefik"
```

### Test Création Projet
```
1. "Crée une API FastAPI appelée test-api"
2. "Crée un site web statique appelé mon-site"
```

### Test Contexte
```
"Analyse le projet ai-orchestrator et explique sa structure"
```

---

*Mis à jour le 9 décembre 2025*
