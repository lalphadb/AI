# Guide de Mise à Niveau - AI Orchestrator v3.0

## Migration de v2.x vers v3.0

### Nouveautés v3.0

- **Authentification JWT** - Tokens d'accès et refresh
- **API Keys** - Pour les intégrations CI/CD
- **Rate Limiting** - Protection contre les abus
- **Validation de sécurité** - Commandes et chemins
- **Audit logging** - Traçabilité complète
- **CORS restrictif** - Configuration par domaine
- **Configuration centralisée** - Variables d'environnement

---

## Étapes de migration

### 1. Backup

```bash
# Sauvegarder les données
cd /home/lalpha/projets/ai-tools/ai-orchestrator
tar -czf backup-v2-$(date +%Y%m%d).tar.gz data/ backend/

# Sauvegarder la DB
cp /data/orchestrator.db /data/orchestrator.db.backup-v2
```

### 2. Mettre à jour les fichiers

```bash
# Copier les nouveaux modules
cp backend/security.py /app/
cp backend/auth.py /app/
cp backend/rate_limiter.py /app/
cp backend/config.py /app/

# Mettre à jour requirements
pip install -r backend/requirements.txt
```

### 3. Configuration

Créez un fichier `.env` dans le répertoire backend:

```bash
# .env
AI_JWT_SECRET_KEY=votre-clé-secrète-32-caractères-minimum
AI_JWT_EXPIRE_MINUTES=60
AI_AUTH_ENABLED=true
AI_ADMIN_PASSWORD=mot-de-passe-fort
AI_CORS_ORIGINS=["https://ai.4lb.ca"]
AI_RATE_LIMIT_ENABLED=true
AI_DEBUG=false
```

### 4. Modifier main.py

Ajoutez les imports au début du fichier:

```python
# Nouveaux imports pour v3.0
from config import get_settings, get_cors_config, MODELS
from security import (
    validate_command,
    validate_path,
    CommandNotAllowedError,
    PathNotAllowedError,
    audit_log
)
from auth import (
    get_current_user,
    get_current_active_user,
    get_optional_user,
    require_scope,
    create_access_token,
    authenticate_user,
    check_login_rate_limit,
    record_login_attempt,
    init_auth_db,
    Token,
    UserCreate,
)
from rate_limiter import RateLimitMiddleware, rate_limiter
```

Remplacez la configuration CORS:

```python
# Avant (v2.x)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Après (v3.0)
from config import get_cors_config
cors_config = get_cors_config()
app.add_middleware(
    CORSMiddleware,
    **cors_config
)
```

Ajoutez le middleware de rate limiting:

```python
# Après le CORS middleware
from rate_limiter import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)
```

### 5. Sécuriser execute_command

```python
# Avant (v2.x)
async def execute_tool(tool_name: str, params: dict, ...):
    if tool_name == "execute_command":
        cmd = params.get("command", "")
        result = subprocess.run(cmd, shell=True, ...)

# Après (v3.0)
from security import validate_command, CommandNotAllowedError

async def execute_tool(tool_name: str, params: dict, ...):
    if tool_name == "execute_command":
        cmd = params.get("command", "")

        # Validation de sécurité
        allowed, reason = validate_command(cmd)
        if not allowed:
            return f"Commande bloquée: {reason}"

        result = subprocess.run(cmd, shell=True, ...)
```

### 6. Sécuriser read_file et write_file

```python
# Pour read_file
from security import validate_path, PathNotAllowedError

elif tool_name == "read_file":
    path = params.get("path", "")
    try:
        path = validate_path(path, write=False)
    except PathNotAllowedError as e:
        return f"Erreur: {e}"
    # ... reste du code

# Pour write_file
elif tool_name == "write_file":
    path = params.get("path", "")
    try:
        path = validate_path(path, write=True)
    except PathNotAllowedError as e:
        return f"Erreur: {e}"
    # ... reste du code
```

### 7. Ajouter les endpoints d'authentification

```python
from fastapi.security import OAuth2PasswordRequestForm

@app.post("/api/auth/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    ip = request.client.host if request.client else "unknown"

    # Rate limiting
    if not check_login_rate_limit(form_data.username, ip):
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts"
        )

    user = authenticate_user(form_data.username, form_data.password)
    record_login_attempt(form_data.username, ip, success=user is not None)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    access_token = create_access_token(
        data={"sub": user.username, "scopes": user.scopes}
    )
    refresh_token = create_refresh_token(...)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600
    )
```

### 8. Protéger les endpoints

```python
# Endpoint nécessitant authentification
@app.post("/api/chat")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user)
):
    # L'utilisateur est authentifié
    ...

# Endpoint avec scope spécifique
@app.delete("/api/conversations/{id}")
async def delete_conversation(
    id: str,
    current_user: User = Depends(require_scope("write"))
):
    ...

# Endpoint admin uniquement
@app.post("/api/auth/users")
async def create_user(
    user: UserCreate,
    current_user: User = Depends(get_current_admin_user)
):
    ...
```

### 9. Mettre à jour le Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl openssh-client procps docker.io git \
    && rm -rf /var/lib/apt/lists/*

RUN git config --global --add safe.directory '*'

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier tous les modules
COPY main.py .
COPY auto_learn.py .
COPY security.py .
COPY auth.py .
COPY rate_limiter.py .
COPY config.py .

RUN mkdir -p /data

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### 10. Mettre à jour docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ai-orchestrator-backend
    restart: unless-stopped
    environment:
      - OLLAMA_URL=http://10.10.10.46:11434
      # Nouvelles variables v3.0
      - AI_JWT_SECRET_KEY=${AI_JWT_SECRET_KEY}
      - AI_AUTH_ENABLED=true
      - AI_ADMIN_PASSWORD=${AI_ADMIN_PASSWORD}
      - AI_RATE_LIMIT_ENABLED=true
      - AI_DEBUG=false
    volumes:
      - ai-orchestrator-data:/data
      - /var/run/docker.sock:/var/run/docker.sock
      - /home/lalpha/.ssh/id_rsa_udm:/home/lalpha/.ssh/id_rsa_udm:ro
    networks:
      - traefik-net
    # ... reste de la config
```

### 11. Reconstruire et déployer

```bash
# Reconstruire l'image
cd /home/lalpha/projets/ai-tools/ai-orchestrator
docker compose build --no-cache

# Redémarrer
docker compose down
docker compose up -d

# Vérifier les logs
docker logs -f ai-orchestrator-backend
```

### 12. Tester

```bash
# Health check
curl https://ai.4lb.ca/health

# Login
curl -X POST https://ai.4lb.ca/api/auth/login \
  -d "username=admin&password=votremotdepasse"

# Test avec token
TOKEN="votre_token"
curl https://ai.4lb.ca/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'
```

---

## Rollback

En cas de problème:

```bash
# Restaurer le backup
cd /home/lalpha/projets/ai-tools/ai-orchestrator
tar -xzf backup-v2-XXXXXXXX.tar.gz

# Restaurer la DB
cp /data/orchestrator.db.backup-v2 /data/orchestrator.db

# Redémarrer avec l'ancienne version
docker compose down
docker compose up -d
```

---

## Breaking Changes

### API

| v2.x | v3.0 | Action |
|------|------|--------|
| `POST /api/chat` sans auth | Requiert `Authorization: Bearer` | Ajouter token |
| CORS `*` | Domaines spécifiques | Configurer `AI_CORS_ORIGINS` |
| Pas de rate limit | 60 req/min par défaut | - |

### Comportement

| v2.x | v3.0 |
|------|------|
| Toutes les commandes autorisées | Whitelist de commandes |
| Tous les chemins accessibles | Chemins validés |
| Pas de logging | Audit logging |

---

## Support

En cas de problème de migration:
1. Consultez les logs: `docker logs ai-orchestrator-backend`
2. Vérifiez la configuration: `/health` endpoint
3. Testez l'authentification manuellement
