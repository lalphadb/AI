#!/usr/bin/env python3
"""
Module d'Authentification JWT pour AI Orchestrator v3.0
Gestion des utilisateurs, tokens et sessions
"""

import hashlib
import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from pydantic import BaseModel

# Charger les variables d'environnement
load_dotenv()

# ===== CONFIGURATION =====

# Clé secrète pour JWT - DOIT être changée en production
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_urlsafe(32)
    print("⚠️ WARNING: JWT_SECRET_KEY not set! Using random key.")
else:
    print("🔐 AUTH: JWT secret loaded from environment")
ALGORITHM = "HS256"
# SECURITE: Tokens a duree de vie reduite (audit 2025-12-30)
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 heure (etait 24h)
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Base de données des utilisateurs
AUTH_DB_PATH = os.getenv("AUTH_DB_PATH", "data/auth.db")

# API Key header pour les intégrations
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# ===== MODÈLES PYDANTIC =====


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: List[str] = []


class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False
    is_admin: bool = False
    scopes: List[str] = []


class UserInDB(User):
    hashed_password: str


class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None


class APIKey(BaseModel):
    key: str
    name: str
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None


# ===== BASE DE DONNÉES =====


def init_auth_db():
    """Initialiser la base de données d'authentification"""
    os.makedirs(os.path.dirname(AUTH_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(AUTH_DB_PATH)
    c = conn.cursor()

    # Table utilisateurs
    c.execute(
        """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT,
        full_name TEXT,
        hashed_password TEXT NOT NULL,
        disabled BOOLEAN DEFAULT FALSE,
        is_admin BOOLEAN DEFAULT FALSE,
        scopes TEXT DEFAULT '[]',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""
    )

    # Table API Keys
    c.execute(
        """CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_hash TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        user_id INTEGER,
        scopes TEXT DEFAULT '[]',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        last_used TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )"""
    )

    # Table sessions
    c.execute(
        """CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        refresh_token_hash TEXT UNIQUE NOT NULL,
        ip_address TEXT,
        user_agent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )"""
    )

    # Table tentatives de connexion (pour rate limiting)
    c.execute(
        """CREATE TABLE IF NOT EXISTS login_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        ip_address TEXT,
        success BOOLEAN,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""
    )

    conn.commit()

    # Créer l'utilisateur admin par défaut s'il n'existe pas
    c.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("admin",))
    if c.fetchone()[0] == 0:
        from config import get_settings

        admin_password = get_settings().admin_password
        hashed = hash_password(admin_password)
        c.execute(
            """INSERT INTO users (username, hashed_password, is_admin, scopes)
                     VALUES (?, ?, TRUE, ?)""",
            ("admin", hashed, '["admin", "read", "write", "execute"]'),
        )
        conn.commit()
        print("Admin user created.")
        print("IMPORTANT: Change the admin password if you haven't set it in .env!")

    conn.close()


def get_auth_db():
    """Obtenir une connexion à la DB d'auth"""
    conn = sqlite3.connect(AUTH_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ===== FONCTIONS DE HACHAGE =====


def hash_password(password: str) -> str:
    """Hasher un mot de passe avec salt"""
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
    return f"{salt}${hashed}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifier un mot de passe"""
    try:
        salt, hashed = hashed_password.split("$")
        new_hash = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode(), salt.encode(), 100000
        ).hex()
        return secrets.compare_digest(new_hash, hashed)
    except Exception:
        return False


def hash_token(token: str) -> str:
    """Hasher un token pour stockage"""
    return hashlib.sha256(token.encode()).hexdigest()


# ===== GESTION DES UTILISATEURS =====


def get_user(username: str) -> Optional[UserInDB]:
    """Récupérer un utilisateur par username"""
    conn = get_auth_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()

    if row:
        import json

        return UserInDB(
            username=row["username"],
            email=row["email"],
            full_name=row["full_name"],
            hashed_password=row["hashed_password"],
            disabled=bool(row["disabled"]),
            is_admin=bool(row["is_admin"]),
            scopes=json.loads(row["scopes"] or "[]"),
        )
    return None


def get_user_by_id(user_id: int) -> Optional[User]:
    """Récupérer un utilisateur par son ID"""
    conn = get_auth_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()

    if row:
        import json

        return User(
            username=row["username"],
            email=row["email"],
            full_name=row["full_name"],
            disabled=bool(row["disabled"]),
            is_admin=bool(row["is_admin"]),
            scopes=json.loads(row["scopes"] or "[]"),
        )
    return None


def get_user_id(username: str) -> Optional[int]:
    """Récupérer l'ID d'un utilisateur par son username"""
    conn = get_auth_db()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()

    if row:
        return row["id"]
    return None


def create_user(user: UserCreate, is_admin: bool = False) -> User:
    """Créer un nouvel utilisateur"""
    conn = get_auth_db()
    c = conn.cursor()

    hashed = hash_password(user.password)
    default_scopes = '["read"]' if not is_admin else '["admin", "read", "write", "execute"]'

    try:
        c.execute(
            """INSERT INTO users (username, email, full_name, hashed_password, is_admin, scopes)
                     VALUES (?, ?, ?, ?, ?, ?)""",
            (user.username, user.email, user.full_name, hashed, is_admin, default_scopes),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists"
        )
    finally:
        conn.close()

    return User(
        username=user.username, email=user.email, full_name=user.full_name, is_admin=is_admin
    )


def update_user(username: str, update: UserUpdate) -> Optional[User]:
    """Mettre à jour un utilisateur"""
    conn = get_auth_db()
    c = conn.cursor()

    updates = []
    values = []

    if update.email is not None:
        updates.append("email = ?")
        values.append(update.email)

    if update.full_name is not None:
        updates.append("full_name = ?")
        values.append(update.full_name)

    if update.password is not None:
        updates.append("hashed_password = ?")
        values.append(hash_password(update.password))

    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(username)
        c.execute(f"""UPDATE users SET {", ".join(updates)} WHERE username = ?""", values)
        conn.commit()

    conn.close()
    return get_user(username)


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authentifier un utilisateur"""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# ===== GESTION DES TOKENS =====


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Créer un token JWT d'accès"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int, ip_address: str = "", user_agent: str = "") -> str:
    """Créer un refresh token"""
    token = secrets.token_urlsafe(64)
    token_hash = hash_token(token)
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    conn = get_auth_db()
    c = conn.cursor()
    c.execute(
        """INSERT INTO sessions (user_id, refresh_token_hash, ip_address, user_agent, expires_at)
                 VALUES (?, ?, ?, ?, ?)""",
        (user_id, token_hash, ip_address, user_agent, expires_at),
    )
    conn.commit()
    conn.close()

    return token


def verify_token(token: str) -> Optional[TokenData]:
    """Vérifier et décoder un token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        scopes: List[str] = payload.get("scopes", [])

        if username is None:
            return None

        return TokenData(username=username, scopes=scopes)
    except jwt.ExpiredSignatureError:
        return None
    except jwt.PyJWTError:
        return None


def verify_refresh_token(token: str) -> Optional[int]:
    """Vérifier un refresh token et retourner l'user_id"""
    token_hash = hash_token(token)

    conn = get_auth_db()
    c = conn.cursor()
    c.execute(
        """SELECT user_id FROM sessions
                 WHERE refresh_token_hash = ? AND expires_at > CURRENT_TIMESTAMP""",
        (token_hash,),
    )
    row = c.fetchone()
    conn.close()

    if row:
        return row["user_id"]
    return None


def revoke_refresh_token(token: str):
    """Révoquer un refresh token"""
    token_hash = hash_token(token)

    conn = get_auth_db()
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE refresh_token_hash = ?", (token_hash,))
    conn.commit()
    conn.close()


# ===== GESTION DES API KEYS =====


def create_api_key(
    name: str, user_id: int, scopes: List[str], expires_days: Optional[int] = None
) -> str:
    """Créer une nouvelle API key"""
    key = f"ak_{secrets.token_urlsafe(32)}"
    key_hash = hash_token(key)
    expires_at = None
    if expires_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_days)

    conn = get_auth_db()
    c = conn.cursor()
    import json

    c.execute(
        """INSERT INTO api_keys (key_hash, name, user_id, scopes, expires_at)
                 VALUES (?, ?, ?, ?, ?)""",
        (key_hash, name, user_id, json.dumps(scopes), expires_at),
    )
    conn.commit()
    conn.close()

    return key


def verify_api_key(key: str) -> Optional[Dict]:
    """Vérifier une API key"""
    if not key or not key.startswith("ak_"):
        return None

    key_hash = hash_token(key)

    conn = get_auth_db()
    c = conn.cursor()
    c.execute(
        """SELECT ak.*, u.username FROM api_keys ak
                 JOIN users u ON ak.user_id = u.id
                 WHERE ak.key_hash = ?
                 AND (ak.expires_at IS NULL OR ak.expires_at > CURRENT_TIMESTAMP)""",
        (key_hash,),
    )
    row = c.fetchone()

    if row:
        # Mettre à jour last_used
        c.execute(
            "UPDATE api_keys SET last_used = CURRENT_TIMESTAMP WHERE key_hash = ?", (key_hash,)
        )
        conn.commit()
        conn.close()

        import json

        return {
            "username": row["username"],
            "name": row["name"],
            "scopes": json.loads(row["scopes"] or "[]"),
        }

    conn.close()
    return None


# ===== RATE LIMITING POUR AUTH =====


def check_login_rate_limit(username: str, ip_address: str) -> bool:
    """Vérifier le rate limit pour les tentatives de connexion"""
    conn = get_auth_db()
    c = conn.cursor()

    # Compter les tentatives échouées dans les 15 dernières minutes
    c.execute(
        """SELECT COUNT(*) FROM login_attempts
                 WHERE (username = ? OR ip_address = ?)
                 AND success = FALSE
                 AND created_at > datetime('now', '-15 minutes')""",
        (username, ip_address),
    )
    count = c.fetchone()[0]
    conn.close()

    # Maximum 5 tentatives échouées par 15 minutes
    return count < 5


def record_login_attempt(username: str, ip_address: str, success: bool):
    """Enregistrer une tentative de connexion"""
    conn = get_auth_db()
    c = conn.cursor()
    c.execute(
        """INSERT INTO login_attempts (username, ip_address, success)
                 VALUES (?, ?, ?)""",
        (username, ip_address, success),
    )
    conn.commit()
    conn.close()


# ===== DÉPENDANCES FASTAPI =====


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Depends(API_KEY_HEADER),
) -> Optional[User]:
    """
    Obtenir l'utilisateur courant depuis le token JWT ou l'API key
    """
    # Essayer d'abord l'API key
    if api_key:
        key_info = verify_api_key(api_key)
        if key_info:
            user = get_user(key_info["username"])
            if user and not user.disabled:
                # Utiliser les scopes de l'API key
                return User(
                    username=user.username,
                    email=user.email,
                    full_name=user.full_name,
                    disabled=user.disabled,
                    is_admin=user.is_admin,
                    scopes=key_info["scopes"],
                )

    # Sinon essayer le token JWT
    if token:
        token_data = verify_token(token)
        if token_data:
            user = get_user(token_data.username)
            if user and not user.disabled:
                return User(
                    username=user.username,
                    email=user.email,
                    full_name=user.full_name,
                    disabled=user.disabled,
                    is_admin=user.is_admin,
                    scopes=token_data.scopes,
                )

    return None


async def get_current_active_user(current_user: Optional[User] = Depends(get_current_user)) -> User:
    """
    Obtenir l'utilisateur courant actif (requis)
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Obtenir l'utilisateur courant admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return current_user


def require_scope(scope: str):
    """
    Décorateur pour exiger un scope spécifique
    """

    async def scope_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if scope not in current_user.scopes and "admin" not in current_user.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Scope '{scope}' required"
            )
        return current_user

    return scope_checker


# ===== OPTIONNEL: AUTH DÉSACTIVABLE =====

AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").lower() == "true"


async def get_optional_user(
    current_user: Optional[User] = Depends(get_current_user),
) -> Optional[User]:
    """
    Obtenir l'utilisateur courant si l'auth est activée
    Retourne un utilisateur avec permissions limitees si l'auth est désactivée
    SECURITE: Ne plus donner admin par defaut (audit 2025-12-30)
    """
    if not AUTH_ENABLED:
        # Auth désactivée - retourner un utilisateur avec permissions LIMITEES
        # SECURITE: Pas de privileges admin sans authentification!
        return User(
            username="anonymous",
            is_admin=False,  # SECURITE: Jamais admin sans auth
            scopes=["read"],  # SECURITE: Lecture seule par defaut
        )
    return current_user


# Initialiser la DB au chargement du module
init_auth_db()
