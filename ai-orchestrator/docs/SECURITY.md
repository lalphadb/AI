# Guide de Sécurité - AI Orchestrator v3.0

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Authentification](#authentification)
3. [Autorisation et Scopes](#autorisation-et-scopes)
4. [Validation des commandes](#validation-des-commandes)
5. [Validation des chemins](#validation-des-chemins)
6. [Rate Limiting](#rate-limiting)
7. [Configuration CORS](#configuration-cors)
8. [Audit et Logging](#audit-et-logging)
9. [Bonnes pratiques](#bonnes-pratiques)
10. [Checklist de déploiement](#checklist-de-déploiement)

---

## Vue d'ensemble

L'AI Orchestrator v3.0 implémente plusieurs couches de sécurité:

```
┌─────────────────────────────────────────────────────┐
│                   Rate Limiting                      │
│              (Protection DDoS/Abus)                 │
├─────────────────────────────────────────────────────┤
│                  CORS Filtering                      │
│            (Origines autorisées)                    │
├─────────────────────────────────────────────────────┤
│              JWT Authentication                      │
│         (Tokens + API Keys)                         │
├─────────────────────────────────────────────────────┤
│              Scope Authorization                     │
│       (read, write, execute, admin)                 │
├─────────────────────────────────────────────────────┤
│           Command Validation                         │
│      (Whitelist + Pattern Detection)                │
├─────────────────────────────────────────────────────┤
│             Path Validation                          │
│     (Chemins autorisés/interdits)                   │
├─────────────────────────────────────────────────────┤
│              Audit Logging                           │
│        (Traçabilité complète)                       │
└─────────────────────────────────────────────────────┘
```

---

## Authentification

### Méthodes d'authentification

#### 1. JWT (JSON Web Tokens)

```bash
# Obtenir un token
curl -X POST https://ai.4lb.ca/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=yourpassword"

# Réponse
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "xyz123...",
  "token_type": "bearer",
  "expires_in": 3600
}

# Utiliser le token
curl https://ai.4lb.ca/api/chat \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

#### 2. API Keys

```bash
# Créer une API key (admin requis)
curl -X POST https://ai.4lb.ca/api/auth/apikeys \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "CI/CD", "scopes": ["read", "execute"]}'

# Réponse
{
  "key": "ak_abc123xyz...",
  "name": "CI/CD",
  "scopes": ["read", "execute"]
}

# Utiliser l'API key
curl https://ai.4lb.ca/api/chat \
  -H "X-API-Key: ak_abc123xyz..."
```

### Configuration

```bash
# Variables d'environnement
export AI_JWT_SECRET_KEY="votre-clé-secrète-de-32-caractères-minimum"
export AI_JWT_EXPIRE_MINUTES=60
export AI_AUTH_ENABLED=true
export AI_ADMIN_PASSWORD="mot-de-passe-fort"
```

### Utilisateur admin par défaut

Au premier démarrage, un utilisateur admin est créé:
- **Username**: `admin`
- **Password**: Valeur de `AI_ADMIN_PASSWORD` ou `changeme123`

**IMPORTANT**: Changez ce mot de passe immédiatement!

---

## Autorisation et Scopes

### Scopes disponibles

| Scope | Description | Permissions |
|-------|-------------|-------------|
| `read` | Lecture seule | Voir fichiers, logs, status |
| `write` | Écriture | Créer/modifier fichiers |
| `execute` | Exécution | Exécuter commandes |
| `admin` | Administration | Tout + gestion utilisateurs |

### Endpoints par scope

```python
# read - accessible à tous les utilisateurs authentifiés
GET /api/conversations
GET /tools
GET /health

# write - nécessite scope "write"
POST /api/upload
PUT /api/conversations/{id}

# execute - nécessite scope "execute"
POST /api/chat  # exécute des commandes
POST /ws/chat

# admin - nécessite scope "admin"
POST /api/auth/users
DELETE /api/auth/users/{id}
POST /api/auth/apikeys
```

### Vérification des scopes dans le code

```python
from auth import require_scope, get_current_active_user

@app.post("/api/sensitive")
async def sensitive_endpoint(
    user = Depends(require_scope("execute"))
):
    # Seuls les utilisateurs avec scope "execute" peuvent accéder
    pass
```

---

## Validation des commandes

### Commandes autorisées (Whitelist)

```python
ALLOWED_COMMANDS = {
    # Système
    "ls", "cat", "head", "tail", "grep", "find",
    "uptime", "hostname", "df", "du", "free",

    # Docker
    "docker",  # Avec sous-commandes limitées

    # Git
    "git",     # Avec sous-commandes limitées

    # Services
    "systemctl",  # Avec services limités
}
```

### Sous-commandes Docker autorisées

```python
ALLOWED_DOCKER_SUBCOMMANDS = {
    "ps", "logs", "inspect", "stats",
    "start", "stop", "restart",
    "exec",  # Limité à certains containers
}

# Containers autorisés pour docker exec
DOCKER_EXEC_WHITELIST = {
    "ai-orchestrator-backend",
    "ai-orchestrator-frontend",
    "chromadb",
    "traefik",
}
```

### Patterns dangereux détectés

```python
DANGEROUS_PATTERNS = [
    r";\s*rm\s+-rf",      # rm -rf après ;
    r"\|\s*sh",            # pipe vers shell
    r"`.*`",               # command substitution
    r"\$\(.*\)",           # $(command)
    r"curl.*\|\s*sh",      # curl pipe shell
    r"eval\s+",            # eval
    r"sudo\s+",            # sudo
]
```

### Exemples

```python
# ✅ Autorisé
validate_command("ls -la /home/lalpha/projets")
validate_command("docker ps")
validate_command("git status")

# ❌ Bloqué
validate_command("rm -rf /")           # Commande dangereuse
validate_command("curl url | sh")      # Pattern dangereux
validate_command("unknowncmd")         # Commande non whitelistée
validate_command("docker run evil")    # Sous-commande non autorisée
```

---

## Validation des chemins

### Chemins autorisés en lecture

```python
ALLOWED_READ_PATHS = [
    "/home/lalpha/projets",
    "/home/lalpha/documentation",
    "/data",
    "/tmp",
    "/var/log",
]
```

### Chemins autorisés en écriture

```python
ALLOWED_WRITE_PATHS = [
    "/home/lalpha/projets",
    "/home/lalpha/scripts",
    "/data",
    "/tmp",
]
```

### Chemins interdits (Blacklist absolue)

```python
FORBIDDEN_PATHS = [
    "/etc/passwd",
    "/etc/shadow",
    "/root",
    "/.ssh",
    ".env",
    "credentials",
    "secret",
    "private_key",
]
```

### Protection contre les traversées

```python
# ❌ Bloqué automatiquement
validate_path("/home/lalpha/projets/../../../etc/passwd")
# Erreur: "Traversée de répertoire interdite"
```

---

## Rate Limiting

### Limites par endpoint

| Endpoint | Limite | Fenêtre |
|----------|--------|---------|
| `/api/chat` | 10 req | 60s |
| `/ws/chat` | 5 conn | 60s |
| `/api/auth/login` | 5 req | 300s |
| `/api/upload` | 20 req | 60s |
| `/health` | 120 req | 60s |
| Défaut | 60 req | 60s |

### Limite globale par IP

- **300 requêtes par minute** par IP

### Ban automatique

- Après **10 violations** consécutives → Ban de **5 minutes**

### Headers de réponse

```http
HTTP/1.1 200 OK
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1734200000

# En cas de dépassement
HTTP/1.1 429 Too Many Requests
Retry-After: 30
```

### Whitelist d'IPs

```python
WHITELIST_IPS = {
    "127.0.0.1",
    "::1",
    "10.10.10.0/24",      # Réseau local
    "192.168.200.0/24",   # Docker network
}
```

### Configuration personnalisée

```python
from rate_limiter import configure_rate_limits, add_whitelist_ip

# Ajouter des limites personnalisées
configure_rate_limits({
    "/api/heavy-endpoint": (5, 60),  # 5 req/min
})

# Ajouter une IP à la whitelist
add_whitelist_ip("203.0.113.50")
```

---

## Configuration CORS

### Configuration restrictive (Production)

```python
# config.py
cors_origins = [
    "https://ai.4lb.ca",
    "https://4lb.ca",
]
```

### Configuration permissive (Développement)

```python
# Avec AI_DEBUG=true
cors_origins = ["*"]
```

### Variables d'environnement

```bash
export AI_CORS_ORIGINS='["https://ai.4lb.ca","https://mon-autre-domaine.com"]'
```

---

## Audit et Logging

### Fichier d'audit

Toutes les actions sensibles sont loggées dans `/data/audit.log`:

```
2024-12-14 18:30:00 - INFO - COMMAND|ALLOWED|user=admin|cmd=docker ps|reason=OK
2024-12-14 18:30:15 - WARNING - COMMAND|BLOCKED|user=user1|cmd=rm -rf /|reason=Pattern dangereux
2024-12-14 18:31:00 - INFO - AUTH|SUCCESS|user=admin|ip=192.168.1.100
2024-12-14 18:31:30 - WARNING - AUTH|FAILED|user=admin|ip=8.8.8.8
2024-12-14 18:32:00 - INFO - FILE|ALLOWED|user=admin|action=read|path=/home/lalpha/projets/README.md
```

### Types d'événements

| Type | Description |
|------|-------------|
| `COMMAND` | Exécution de commande |
| `FILE` | Accès fichier |
| `AUTH` | Authentification |
| `SECURITY` | Événement de sécurité |

### Analyse des logs

```bash
# Voir les tentatives bloquées
grep "BLOCKED" /data/audit.log

# Voir les échecs d'auth
grep "AUTH|FAILED" /data/audit.log

# Compter par utilisateur
grep "COMMAND" /data/audit.log | cut -d'|' -f3 | sort | uniq -c
```

---

## Bonnes pratiques

### 1. Secrets

```bash
# Générer une clé secrète forte
openssl rand -base64 32

# Ne JAMAIS commiter les secrets
echo ".env" >> .gitignore
```

### 2. Mot de passe admin

```bash
# Changer le mot de passe admin au premier démarrage
curl -X PUT https://ai.4lb.ca/api/auth/users/admin \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"password": "nouveau-mot-de-passe-fort-32-chars"}'
```

### 3. API Keys

- Utilisez des API keys avec **scopes minimaux**
- **Rotez** les clés régulièrement
- **Révokez** immédiatement les clés compromises

### 4. Monitoring

```bash
# Surveiller les tentatives de connexion échouées
tail -f /data/audit.log | grep "FAILED"

# Alerter sur les violations de rate limit
tail -f /var/log/syslog | grep "Rate limit exceeded"
```

### 5. Mise à jour

- Appliquez les mises à jour de sécurité régulièrement
- Surveillez les CVE des dépendances
- Utilisez `pip-audit` ou `safety` pour scanner les vulnérabilités

---

## Checklist de déploiement

### Avant la mise en production

- [ ] Changer `AI_JWT_SECRET_KEY` (minimum 32 caractères)
- [ ] Changer `AI_ADMIN_PASSWORD`
- [ ] Configurer `AI_CORS_ORIGINS` avec vos domaines
- [ ] Vérifier `AI_AUTH_ENABLED=true`
- [ ] Vérifier `AI_RATE_LIMIT_ENABLED=true`
- [ ] Configurer HTTPS (TLS 1.2+)
- [ ] Configurer les headers de sécurité (CSP, HSTS, etc.)
- [ ] Mettre en place la rotation des logs
- [ ] Configurer les alertes de sécurité
- [ ] Tester le rate limiting
- [ ] Tester les validations de commandes
- [ ] Vérifier les permissions de fichiers

### Commandes de test

```bash
# Tester l'authentification
curl -X POST https://ai.4lb.ca/api/auth/login \
  -d "username=admin&password=test"

# Tester le rate limiting
for i in {1..15}; do
  curl -s -o /dev/null -w "%{http_code}\n" https://ai.4lb.ca/api/chat
done

# Tester la validation de commande (doit être bloqué)
curl -X POST https://ai.4lb.ca/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message": "exécute rm -rf /"}'
```

---

## Support

En cas de problème de sécurité:
1. Vérifiez les logs d'audit
2. Consultez cette documentation
3. Contactez l'administrateur système

**Signaler une vulnérabilité**: security@4lb.ca
