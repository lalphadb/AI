# Specification: Audit Complet et Plan de Corrections pour AI Orchestrator v5.2

## Overview

Ce projet vise a realiser un audit complet de securite et de qualite du code pour AI Orchestrator v5.2, un agent autonome FastAPI utilisant une boucle ReAct (Reason-Act-Observe). L'audit couvrira 5 domaines critiques: securite, qualite du code, architecture, performance, et Docker/deploiement. L'objectif est d'identifier et corriger toutes les vulnerabilites CRITICAL et HIGH, tout en maintenant la compatibilite API et la fonctionnalite existante.

## Workflow Type

**Type**: investigation

**Rationale**: Cette tache necessite d'abord une phase d'investigation approfondie (audit avec outils specialises: Ruff, Pylint, pip-audit, Vulture) avant de passer a la correction. Le workflow investigation permet de documenter exhaustivement les problemes avant d'agir, ce qui est essentiel pour un audit de securite.

## Task Scope

### Services Involved
- **backend** (primary) - Application FastAPI avec authentification JWT, boucle ReAct, 34+ outils, memoire semantique ChromaDB
- **frontend** (reference) - Interface nginx servant les fichiers statiques

### This Task Will:
- [ ] Auditer la securite: credentials hardcodes, validation inputs, implementation JWT, permissions, vulnerabilites dependencies
- [ ] Analyser la qualite du code avec Ruff (remplace Bandit), Pylint (score 9.0+), Vulture (dead code)
- [ ] Scanner les dependances avec pip-audit pour vulnerabilites connues
- [ ] Evaluer l'architecture: separation des responsabilites, patterns, couplage
- [ ] Auditer le Dockerfile et docker-compose.yml pour securite et optimisations
- [ ] Produire un rapport d'audit avec severite (CRITICAL/HIGH/MEDIUM/LOW)
- [ ] Corriger toutes les issues CRITICAL et HIGH
- [ ] Ajouter des tests unitaires pour les corrections
- [ ] Documenter tous les changements

### Out of Scope:
- Refactoring majeur de l'architecture (seulement corrections ciblees)
- Migration vers un autre framework ou base de donnees
- Issues MEDIUM/LOW (documentees mais non corrigees dans cette phase)
- Modifications de l'interface frontend
- Ajout de nouvelles fonctionnalites

## Service Context

### Backend

**Tech Stack:**
- Language: Python 3.12
- Framework: FastAPI 0.115.0 avec Pydantic 2.9.2
- Authentication: PyJWT 2.9.0 (python-jose 3.3.0 deprecated - A SUPPRIMER)
- Database: SQLite (auth.db, orchestrator.db)
- Vector DB: chromadb-client (client leger pour ChromaDB server)
- Key directories: `backend/`, `backend/tools/`, `backend/services/`, `backend/tests/`, `backend/utils/`

**Entry Point:** `backend/main.py`

**How to Run:**
```bash
docker compose build backend && docker compose up -d backend
```

**Port:** 8001

**Health Check:**
```bash
curl -s http://localhost:8001/health
```

### Frontend

**Tech Stack:**
- nginx:alpine serving static HTML/CSS/JS

**Port:** 80 (proxied via Traefik)

## Files to Modify

| File | Service | What to Change |
|------|---------|---------------|
| `backend/requirements.txt` | backend | Supprimer python-jose (deprecated), ajouter outils d'audit dev |
| `backend/auth.py` | backend | Corriger JWT implementation, datetime.utcnow() deprecated |
| `backend/security.py` | backend | Ajouter validation plus stricte si issues detectees |
| `backend/main.py` | backend | Corriger warnings Ruff/Pylint identifies |
| `backend/engine.py` | backend | Corriger warnings Ruff/Pylint identifies |
| `backend/config.py` | backend | Securiser la gestion des secrets |
| `backend/Dockerfile` | backend | Optimiser (multi-stage build, non-root user) |
| `docker-compose.yml` | root | Ajouter resource limits (mem_limit: 2G, cpus: 2.0) si absents |
| `backend/tools/*.py` | backend | Corriger issues securite dans les outils |
| `pyproject.toml` | root | Creer config unifiee pour Ruff, Pylint, pytest |

## Files to Reference

These files show patterns to follow:

| File | Pattern to Copy |
|------|----------------|
| `backend/tests/test_security.py` | Structure pytest avec classes de test, assertions claires |
| `backend/security.py` | Pattern de validation avec tuple (allowed, reason) |
| `backend/auth.py` | Pattern de gestion JWT et hash passwords |
| `CLAUDE.md` | Standards de code et commandes de validation |

## Patterns to Follow

### Test Structure Pattern

From `backend/tests/test_security.py`:

```python
class TestCommandValidation:
    """Tests pour la validation des commandes"""

    def test_allowed_simple_commands(self):
        """Les commandes simples doivent etre autorisees"""
        commands = ["ls -la", "grep 'pattern' file.txt"]
        for cmd in commands:
            allowed, reason = validate_command(cmd)
            assert allowed, f"Command should be allowed: {cmd} (Reason: {reason})"
```

**Key Points:**
- Grouper les tests par fonctionnalite dans des classes
- Docstrings descriptives pour chaque test
- Messages d'erreur explicites dans les assertions
- Tester les cas positifs ET negatifs

### Security Validation Pattern

From `backend/security.py`:

```python
def validate_command(command: str) -> Tuple[bool, str]:
    """Valider une commande - Mode autonome = blacklist"""
    if not command or not command.strip():
        return False, "Commande vide"

    # Verifier blacklist
    if base_cmd in FORBIDDEN_COMMANDS:
        logger.warning(f"Commande interdite: {base_cmd}")
        return False, f"Commande '{base_cmd}' interdite"

    return True, "OK"
```

**Key Points:**
- Retourner un tuple (success, reason) pour debugging
- Toujours logger les tentatives bloquees
- Validation defensive (check empty first)

## Requirements

### Functional Requirements

1. **Audit de Securite Complet**
   - Description: Scanner tous les fichiers Python pour credentials hardcodes, secrets exposes, failles de securite
   - Acceptance: Rapport genere avec 0 issues CRITICAL non resolues

2. **Qualite du Code Validee**
   - Description: Atteindre un score Pylint >= 9.0 et 0 erreurs Ruff
   - Acceptance: `ruff check --select=E,F,I,S,B,C4,UP backend/` retourne 0 erreurs, `pylint --fail-under=9.0 backend/` passe

3. **Dependencies Securisees**
   - Description: Scanner toutes les dependances pour vulnerabilites connues
   - Acceptance: `pip-audit -r requirements.txt` retourne 0 vulnerabilites

4. **Dead Code Elimine**
   - Description: Identifier et supprimer le code mort
   - Acceptance: `vulture backend/ --min-confidence 100` ne detecte que les faux positifs documentes

5. **Tests des Corrections**
   - Description: Chaque correction CRITICAL/HIGH doit avoir un test unitaire
   - Acceptance: `pytest backend/tests/ -v` passe a 100%

### Edge Cases

1. **python-jose vs PyJWT** - Le projet utilise les deux; migrer vers PyJWT uniquement car python-jose est deprecated
2. **datetime.utcnow() deprecated** - Remplacer par datetime.now(timezone.utc) dans tout le code:
   ```python
   # AVANT (deprecated)
   from datetime import datetime
   now = datetime.utcnow()

   # APRES (correct)
   from datetime import datetime, timezone
   now = datetime.now(timezone.utc)
   ```
3. **Secrets en fallback** - Le code genere des secrets aleatoires si non configures; documenter ce comportement
4. **Symlinks malicieux** - La fonction sanitize_path les detecte deja; verifier la couverture de tests

## Implementation Notes

### pyproject.toml Configuration (a creer)

```toml
[project]
name = "ai-orchestrator"
version = "5.2.0"
requires-python = ">=3.12"

[tool.ruff]
target-version = "py312"
line-length = 100
select = ["E", "F", "I", "S", "B", "C4", "UP"]
ignore = ["S101"]  # Allow assert in tests

[tool.ruff.per-file-ignores]
"tests/*" = ["S101", "S106"]  # Allow asserts and hardcoded passwords in tests

[tool.pylint.main]
fail-under = 9.0
max-line-length = 100
disable = ["C0114", "C0115", "C0116"]  # Missing docstrings

[tool.pytest.ini_options]
testpaths = ["backend/tests"]
addopts = "--cov=backend --cov-report=term-missing --cov-fail-under=80"
filterwarnings = ["ignore::ResourceWarning"]

[tool.vulture]
min_confidence = 100
paths = ["backend/"]
```

### DO
- Utiliser Ruff comme linter principal (remplace Bandit pour les regles S)
- Centraliser la config dans pyproject.toml
- Creer des backups avant modification: `cp fichier.py fichier.py.backup.$(date +%Y%m%d)`
- Verifier la syntaxe avec `python3 -m py_compile` apres chaque edit
- Executer `docker compose build backend` apres modifications pour valider
- Maintenir la compatibilite avec l'API existante

### DON'T
- Ne pas casser les fonctionnalites existantes (P0 critiques dans CLAUDE.md)
- Ne pas modifier les interfaces publiques des outils
- Ne pas supprimer de code sans verifier qu'il n'est pas utilise dynamiquement
- Ne pas commiter de secrets dans le code
- Ne pas ignorer les warnings de securite

## Development Environment

### Start Services

```bash
# Rebuild et redemarrage backend
docker compose build backend && docker compose up -d backend

# Voir les logs
docker logs -f ai-orchestrator-backend

# Verifier la sante
curl -s http://localhost:8001/health | jq
```

### Service URLs
- Backend API: http://localhost:8001
- Health endpoint: http://localhost:8001/health
- Stats endpoint: http://localhost:8001/api/stats

### Required Environment Variables
- `JWT_SECRET_KEY`: Cle secrete pour signature JWT (OBLIGATOIRE en production)
- `ADMIN_PASSWORD`: Mot de passe admin (defaut genere si absent)
- `AUTH_ENABLED`: true/false pour activer l'authentification
- `OLLAMA_URL`: URL du serveur Ollama (http://host.docker.internal:11434)
- `CHROMADB_HOST`: Host ChromaDB
- `CHROMADB_PORT`: Port ChromaDB (8000)

### Audit Commands

```bash
# Installation des outils d'audit (versions minimales recommandees)
pip install "ruff>=0.14.10" "pylint>=3.0.0" "vulture>=2.11" "pip-audit>=2.7.0" "pytest-cov>=5.0.0"

# Scan securite avec Ruff (inclut les regles S = security, I = imports, B = bugbear, C4 = comprehensions, UP = pyupgrade)
ruff check --select=E,F,I,S,B,C4,UP backend/

# Score Pylint
pylint --fail-under=9.0 backend/

# Detection code mort
vulture backend/ --min-confidence 100

# Scan vulnerabilites dependencies
pip-audit -r backend/requirements.txt

# Couverture de tests
pytest backend/tests/ --cov=backend --cov-report=html --cov-fail-under=80
```

## Success Criteria

The task is complete when:

1. [ ] Rapport d'audit genere avec classification CRITICAL/HIGH/MEDIUM/LOW
2. [ ] Toutes les issues CRITICAL corrigees avec tests
3. [ ] Toutes les issues HIGH corrigees avec tests
4. [ ] Score Pylint >= 9.0 sur tous les fichiers Python
5. [ ] 0 erreurs Ruff (E,F,S rules)
6. [ ] 0 vulnerabilites pip-audit
7. [ ] python-jose remplace par PyJWT uniquement
8. [ ] datetime.utcnow() remplace partout
9. [ ] pyproject.toml cree avec config unifiee
10. [ ] Dockerfile optimise (non-root user, multi-stage si benefique)
11. [ ] Tous les tests existants passent
12. [ ] Docker build reussit sans erreurs
13. [ ] Health check passe apres deploiement
14. [ ] Documentation des changements dans CHANGELOG

## QA Acceptance Criteria

**CRITICAL**: These criteria must be verified by the QA Agent before sign-off.

### Unit Tests
| Test | File | What to Verify |
|------|------|----------------|
| test_jwt_security | `backend/tests/test_auth.py` | Tokens expirent correctement, refresh token fonctionne |
| test_command_validation | `backend/tests/test_security.py` | Toutes les commandes blacklistees sont bloquees |
| test_path_validation | `backend/tests/test_security.py` | Traversee de repertoire bloquee, symlinks verifies |
| test_rate_limiting | `backend/tests/test_rate_limiter.py` | Rate limits respectes, pas de bypass |

### Integration Tests
| Test | Services | What to Verify |
|------|----------|----------------|
| API Authentication Flow | backend | Login -> Get Token -> Access Protected -> Refresh -> Logout |
| Tool Execution Security | backend | execute_command valide les commandes avant execution |
| File Access Security | backend | read_file/write_file respectent les permissions |

### End-to-End Tests
| Flow | Steps | Expected Outcome |
|------|-------|------------------|
| Secure Command Execution | 1. Tenter `mkfs /dev/sda` 2. Verifier blocage | Commande bloquee, log audit genere |
| JWT Token Lifecycle | 1. Login 2. Attendre expiration 3. Tenter acces | 401 Unauthorized apres expiration |
| Path Traversal Prevention | 1. Tenter `/data/../etc/passwd` | Acces refuse, exception levee |

### Browser Verification (if frontend)
| Page/Component | URL | Checks |
|----------------|-----|--------|
| Health Status | `http://localhost:8001/health` | Retourne {"status": "ok"} |
| API Stats | `http://localhost:8001/api/stats` | Retourne statistiques valides |

### Database Verification (if applicable)
| Check | Query/Command | Expected |
|-------|---------------|----------|
| Auth tables exist | `sqlite3 data/auth.db ".tables"` | users, api_keys, sessions, login_attempts |
| Admin user exists | `SELECT username FROM users WHERE is_admin=1` | admin |
| No plaintext passwords | `SELECT hashed_password FROM users LIMIT 1` | Hash format: salt$hash |

### Code Quality Verification
| Check | Command | Expected |
|-------|---------|----------|
| Syntax validation | `python3 -m py_compile backend/*.py` | Exit code 0 |
| Ruff clean | `ruff check --select=E,F,I,S,B,C4,UP backend/` | 0 errors |
| Pylint score | `pylint --fail-under=9.0 backend/` | Score >= 9.0 |
| No vulnerabilities | `pip-audit -r backend/requirements.txt` | 0 vulnerabilities |
| Tests pass | `pytest backend/tests/ -v` | All tests pass |
| Coverage | `pytest --cov=backend --cov-fail-under=80` | >= 80% coverage |

### Security Verification
| Check | Method | Expected |
|-------|--------|----------|
| No hardcoded secrets | `ruff check --select=S105,S106,S107 backend/` | 0 issues |
| JWT secret from env | Check auth.py | SECRET_KEY from os.getenv() |
| Passwords hashed | Check auth.py | pbkdf2_hmac with salt |
| Command blacklist active | Check security.py | FORBIDDEN_COMMANDS populated |

### QA Sign-off Requirements
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All E2E tests pass
- [ ] Browser verification complete (if applicable)
- [ ] Database state verified (if applicable)
- [ ] No regressions in existing functionality
- [ ] Code follows established patterns
- [ ] No security vulnerabilities introduced
- [ ] Pylint score >= 9.0
- [ ] 0 Ruff errors
- [ ] 0 pip-audit vulnerabilities
- [ ] Docker build succeeds
- [ ] Health check passes after deployment
