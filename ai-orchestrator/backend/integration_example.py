#!/usr/bin/env python3
"""
Exemple d'intégration des modules de sécurité v3.0
Ce fichier montre comment intégrer les nouveaux modules dans main.py

INSTRUCTIONS:
1. Copiez les sections pertinentes dans votre main.py
2. Ajoutez les imports au début du fichier
3. Modifiez les fonctions existantes selon les exemples
"""

# ============================================================
# SECTION 1: IMPORTS À AJOUTER AU DÉBUT DE main.py
# ============================================================

"""
# Après les imports existants, ajoutez:

from config import get_settings, get_cors_config, MODELS
from security import (
    validate_command,
    validate_path,
    is_path_allowed,
    CommandNotAllowedError,
    PathNotAllowedError,
    audit_log,
    get_security_config,
)
from auth import (
    get_current_user,
    get_current_active_user,
    get_optional_user,
    get_current_admin_user,
    require_scope,
    create_access_token,
    create_refresh_token,
    authenticate_user,
    create_user,
    verify_refresh_token,
    revoke_refresh_token,
    check_login_rate_limit,
    record_login_attempt,
    create_api_key,
    init_auth_db,
    Token,
    User,
    UserCreate,
    UserUpdate,
    AUTH_ENABLED,
)
from rate_limiter import RateLimitMiddleware, rate_limiter, get_rate_limit_stats
"""

# ============================================================
# SECTION 2: CONFIGURATION CORS (remplacer l'existant)
# ============================================================

"""
# AVANT (dans main.py):
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# APRÈS:
from config import get_cors_config
cors_config = get_cors_config()
app.add_middleware(
    CORSMiddleware,
    **cors_config
)

# Ajouter le rate limiting APRÈS le CORS:
app.add_middleware(RateLimitMiddleware)
"""

# ============================================================
# SECTION 3: SÉCURISER execute_command
# ============================================================

async def secure_execute_command(command: str, user: str = "anonymous") -> str:
    """
    Version sécurisée de execute_command

    Remplacez le bloc elif tool_name == "execute_command": dans execute_tool()
    """
    from security import validate_command, audit_log
    import subprocess

    if not command:
        return "Erreur: commande vide"

    # Validation de sécurité
    allowed, reason = validate_command(command)
    audit_log.log_command(command, user=user, allowed=allowed, reason=reason)

    if not allowed:
        return f"Commande bloquée pour des raisons de sécurité: {reason}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        output = result.stdout or result.stderr or "(aucune sortie)"
        return f"Commande: {command}\nSortie:\n{output[:3000]}"
    except subprocess.TimeoutExpired:
        return f"Timeout: la commande a pris trop de temps"
    except Exception as e:
        return f"Erreur: {str(e)}"

# ============================================================
# SECTION 4: SÉCURISER read_file
# ============================================================

async def secure_read_file(path: str, user: str = "anonymous") -> str:
    """
    Version sécurisée de read_file

    Remplacez le bloc elif tool_name == "read_file": dans execute_tool()
    """
    from security import validate_path, PathNotAllowedError, audit_log
    import os

    if not path:
        return "Erreur: chemin requis"

    # Validation du chemin
    try:
        validated_path = validate_path(path, write=False)
        audit_log.log_file_access(path, "read", user=user, allowed=True)
    except PathNotAllowedError as e:
        audit_log.log_file_access(path, "read", user=user, allowed=False, reason=str(e))
        return f"Accès refusé: {e}"

    if not os.path.exists(validated_path):
        return f"Erreur: fichier non trouvé: {validated_path}"

    try:
        with open(validated_path, 'r', encoding='utf-8') as f:
            content = f.read(10000)
        return f"Contenu de {validated_path}:\n{content}"
    except Exception as e:
        return f"Erreur lecture: {e}"

# ============================================================
# SECTION 5: SÉCURISER write_file
# ============================================================

async def secure_write_file(path: str, content: str, user: str = "anonymous") -> str:
    """
    Version sécurisée de write_file

    Remplacez le bloc elif tool_name == "write_file": dans execute_tool()
    """
    from security import validate_path, PathNotAllowedError, audit_log
    import os

    if not path:
        return "Erreur: chemin requis"

    # Validation du chemin (écriture)
    try:
        validated_path = validate_path(path, write=True)
        audit_log.log_file_access(path, "write", user=user, allowed=True)
    except PathNotAllowedError as e:
        audit_log.log_file_access(path, "write", user=user, allowed=False, reason=str(e))
        return f"Accès refusé: {e}"

    try:
        os.makedirs(os.path.dirname(validated_path), exist_ok=True)
        with open(validated_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Fichier écrit: {validated_path} ({len(content)} caractères)"
    except Exception as e:
        return f"Erreur écriture: {e}"

# ============================================================
# SECTION 6: ENDPOINTS D'AUTHENTIFICATION
# ============================================================

"""
Ajoutez ces endpoints dans main.py après les autres endpoints:
"""

from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm

# --- Login ---
"""
@app.post("/api/auth/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    ip = request.client.host if request.client else "unknown"

    # Rate limiting pour les tentatives de login
    if not check_login_rate_limit(form_data.username, ip):
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again later."
        )

    # Authentification
    user = authenticate_user(form_data.username, form_data.password)
    record_login_attempt(form_data.username, ip, success=user is not None)
    audit_log.log_auth(form_data.username, success=user is not None, ip=ip)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    if user.disabled:
        raise HTTPException(
            status_code=403,
            detail="Account disabled"
        )

    # Créer les tokens
    access_token = create_access_token(
        data={"sub": user.username, "scopes": user.scopes}
    )
    refresh_token = create_refresh_token(
        user_id=1,  # À remplacer par l'ID réel
        ip_address=ip,
        user_agent=request.headers.get("User-Agent", "")
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=3600
    )
"""

# --- Refresh Token ---
"""
@app.post("/api/auth/refresh")
async def refresh_token(refresh_token: str):
    user_id = verify_refresh_token(refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Récupérer l'utilisateur et créer un nouveau token
    # ...
"""

# --- Logout ---
"""
@app.post("/api/auth/logout")
async def logout(
    refresh_token: str,
    current_user: User = Depends(get_current_active_user)
):
    revoke_refresh_token(refresh_token)
    return {"message": "Logged out successfully"}
"""

# --- Me (info utilisateur courant) ---
"""
@app.get("/api/auth/me")
async def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user
"""

# --- Créer un utilisateur (admin) ---
"""
@app.post("/api/auth/users")
async def create_new_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_admin_user)
):
    return create_user(user_data)
"""

# --- Créer une API key (admin) ---
"""
@app.post("/api/auth/apikeys")
async def create_new_api_key(
    name: str,
    scopes: List[str],
    expires_days: Optional[int] = None,
    current_user: User = Depends(get_current_admin_user)
):
    key = create_api_key(name, user_id=1, scopes=scopes, expires_days=expires_days)
    return {"key": key, "name": name, "scopes": scopes}
"""

# ============================================================
# SECTION 7: PROTÉGER LES ENDPOINTS EXISTANTS
# ============================================================

"""
# Pour un endpoint qui nécessite une authentification:
@app.post("/api/chat")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user)  # AJOUTER CECI
):
    # Le reste du code...

# Pour un endpoint avec scope spécifique:
@app.delete("/api/conversations/{conversation_id}")
async def delete_conv(
    conversation_id: str,
    current_user: User = Depends(require_scope("write"))  # AJOUTER CECI
):
    # Le reste du code...

# Pour le WebSocket (optionnel - vérifier le token dans la query string):
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()

    # Optionnel: vérifier le token
    token = websocket.query_params.get("token")
    if AUTH_ENABLED and token:
        from auth import verify_token, get_user
        token_data = verify_token(token)
        if not token_data:
            await websocket.close(code=4001, reason="Invalid token")
            return
        user = get_user(token_data.username)
    else:
        user = None  # Ou utilisateur anonyme

    # Le reste du code...
"""

# ============================================================
# SECTION 8: ENDPOINT DE SÉCURITÉ
# ============================================================

"""
# Ajouter un endpoint pour voir la config de sécurité (admin):
@app.get("/api/security/config")
async def get_security_config_endpoint(
    current_user: User = Depends(get_current_admin_user)
):
    from security import get_security_config
    return get_security_config()

# Ajouter un endpoint pour les stats de rate limiting (admin):
@app.get("/api/security/rate-limit-stats")
async def get_rate_limit_stats_endpoint(
    current_user: User = Depends(get_current_admin_user)
):
    return await get_rate_limit_stats()
"""

# ============================================================
# SECTION 9: INITIALISATION AU DÉMARRAGE
# ============================================================

"""
# Dans la fonction lifespan (ou au démarrage de l'app):
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialiser les DBs
    init_db()
    init_auth_db()  # AJOUTER CECI

    # Démarrer la tâche de nettoyage du rate limiter
    from rate_limiter import cleanup_task
    import asyncio
    asyncio.create_task(cleanup_task())  # AJOUTER CECI

    yield
"""

if __name__ == "__main__":
    print("Ce fichier est un exemple d'intégration.")
    print("Copiez les sections pertinentes dans votre main.py")
    print("")
    print("Fichiers créés:")
    print("  - security.py     : Validation commandes/chemins")
    print("  - auth.py         : Authentification JWT")
    print("  - rate_limiter.py : Rate limiting")
    print("  - config.py       : Configuration centralisée")
    print("")
    print("Documentation:")
    print("  - docs/SECURITY.md : Guide de sécurité")
    print("  - docs/API.md      : Documentation API")
    print("  - docs/UPGRADE.md  : Guide de migration")
