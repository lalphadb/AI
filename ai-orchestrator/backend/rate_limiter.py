#!/usr/bin/env python3
"""
Module de Rate Limiting pour AI Orchestrator v3.0
Protection contre les abus et le DDoS
"""

import os
import time
import asyncio
from typing import Dict, Optional, Callable
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("rate_limiter")

# ===== CONFIGURATION =====

# Limites par défaut (requêtes par fenêtre de temps)
DEFAULT_RATE_LIMITS = {
    # Endpoint: (requests, window_seconds)
    "/api/chat": (10, 60),           # 10 requêtes par minute
    "/ws/chat": (5, 60),              # 5 connexions WebSocket par minute
    "/api/auth/login": (5, 300),      # 5 tentatives par 5 minutes
    "/api/upload": (20, 60),          # 20 uploads par minute
    "/api/conversations": (60, 60),   # 60 requêtes par minute
    "/tools": (30, 60),               # 30 requêtes par minute
    "/health": (120, 60),             # 120 requêtes par minute
    "/api/stats": (120, 60),          # 120 requêtes par minute (polling)
    "default": (60, 60),              # 60 requêtes par minute par défaut
}

# Limites globales par IP
GLOBAL_IP_LIMIT = (300, 60)  # 300 requêtes par minute par IP

# IPs whitelist (pas de rate limiting)
WHITELIST_IPS = {
    "127.0.0.1",
    "::1",
    "10.10.10.0/24",  # Réseau local
    "192.168.200.0/24",  # Docker network
}

# Durée du ban automatique en cas d'abus
BAN_DURATION_SECONDS = 300  # 5 minutes

# Seuil pour déclencher un ban
BAN_THRESHOLD_VIOLATIONS = 10  # 10 violations = ban

# ===== STRUCTURES DE DONNÉES =====

@dataclass
class RateLimitState:
    """État du rate limit pour une clé"""
    requests: int = 0
    window_start: float = field(default_factory=time.time)
    violations: int = 0
    banned_until: Optional[float] = None

@dataclass
class RateLimitResult:
    """Résultat d'une vérification de rate limit"""
    allowed: bool
    remaining: int
    reset_at: float
    retry_after: Optional[int] = None

# ===== STOCKAGE EN MÉMOIRE =====

class InMemoryStorage:
    """Stockage en mémoire pour le rate limiting"""

    def __init__(self):
        self._data: Dict[str, RateLimitState] = defaultdict(RateLimitState)
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> RateLimitState:
        async with self._lock:
            return self._data[key]

    async def set(self, key: str, state: RateLimitState):
        async with self._lock:
            self._data[key] = state

    async def increment(self, key: str, window_seconds: int) -> RateLimitState:
        async with self._lock:
            state = self._data[key]
            now = time.time()

            # Réinitialiser si la fenêtre est expirée
            if now - state.window_start >= window_seconds:
                state.requests = 0
                state.window_start = now

            state.requests += 1
            self._data[key] = state
            return state

    async def add_violation(self, key: str) -> int:
        async with self._lock:
            state = self._data[key]
            state.violations += 1

            # Vérifier si on doit bannir
            if state.violations >= BAN_THRESHOLD_VIOLATIONS:
                state.banned_until = time.time() + BAN_DURATION_SECONDS
                state.violations = 0
                logger.warning(f"IP/User banned: {key}")

            self._data[key] = state
            return state.violations

    async def is_banned(self, key: str) -> bool:
        async with self._lock:
            state = self._data[key]
            if state.banned_until:
                if time.time() < state.banned_until:
                    return True
                else:
                    # Le ban a expiré
                    state.banned_until = None
                    self._data[key] = state
            return False

    async def cleanup(self, max_age_seconds: int = 3600):
        """Nettoyer les entrées expirées"""
        async with self._lock:
            now = time.time()
            keys_to_delete = []
            for key, state in self._data.items():
                if now - state.window_start > max_age_seconds:
                    if not state.banned_until or state.banned_until < now:
                        keys_to_delete.append(key)
            for key in keys_to_delete:
                del self._data[key]

# Instance globale du stockage
storage = InMemoryStorage()

# ===== FONCTIONS UTILITAIRES =====

def get_client_ip(request: Request) -> str:
    """Extraire l'IP client d'une requête"""
    # Vérifier les headers de proxy
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # IP directe
    if request.client:
        return request.client.host

    return "unknown"

def is_ip_whitelisted(ip: str) -> bool:
    """Vérifier si une IP est dans la whitelist"""
    if ip in WHITELIST_IPS:
        return True

    # Vérifier les plages CIDR
    import ipaddress
    try:
        client_ip = ipaddress.ip_address(ip)
        for whitelisted in WHITELIST_IPS:
            if "/" in whitelisted:
                network = ipaddress.ip_network(whitelisted, strict=False)
                if client_ip in network:
                    return True
    except ValueError:
        pass

    return False

def get_rate_limit_for_path(path: str) -> tuple:
    """Obtenir les limites pour un chemin"""
    # Correspondance exacte
    if path in DEFAULT_RATE_LIMITS:
        return DEFAULT_RATE_LIMITS[path]

    # Correspondance par préfixe
    for route, limits in DEFAULT_RATE_LIMITS.items():
        if route != "default" and path.startswith(route):
            return limits

    return DEFAULT_RATE_LIMITS["default"]

# ===== RATE LIMITER PRINCIPAL =====

class RateLimiter:
    """Rate limiter principal"""

    def __init__(self, storage: InMemoryStorage = storage):
        self.storage = storage

    async def check(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> RateLimitResult:
        """
        Vérifier si une requête est autorisée

        Args:
            key: Clé unique (IP, user_id, etc.)
            max_requests: Nombre maximum de requêtes
            window_seconds: Fenêtre de temps en secondes

        Returns:
            RateLimitResult avec le statut
        """
        # Vérifier si banni
        if await self.storage.is_banned(key):
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_at=time.time() + BAN_DURATION_SECONDS,
                retry_after=BAN_DURATION_SECONDS
            )

        # Incrémenter et vérifier
        state = await self.storage.increment(key, window_seconds)
        remaining = max(0, max_requests - state.requests)
        reset_at = state.window_start + window_seconds

        if state.requests > max_requests:
            # Violation - ajouter à la comptabilité
            await self.storage.add_violation(key)
            retry_after = int(reset_at - time.time())

            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_at=reset_at,
                retry_after=max(1, retry_after)
            )

        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            reset_at=reset_at
        )

    async def check_request(self, request: Request, user_id: Optional[str] = None) -> RateLimitResult:
        """
        Vérifier une requête HTTP

        Args:
            request: Requête FastAPI
            user_id: ID utilisateur optionnel

        Returns:
            RateLimitResult
        """
        ip = get_client_ip(request)
        path = request.url.path

        # Whitelist
        if is_ip_whitelisted(ip):
            return RateLimitResult(allowed=True, remaining=999, reset_at=time.time() + 60)

        # Vérifier la limite globale par IP
        global_key = f"global:{ip}"
        global_result = await self.check(global_key, *GLOBAL_IP_LIMIT)
        if not global_result.allowed:
            return global_result

        # Vérifier la limite par endpoint
        max_requests, window_seconds = get_rate_limit_for_path(path)
        endpoint_key = f"endpoint:{ip}:{path}"

        # Si user_id fourni, utiliser une limite par utilisateur aussi
        if user_id:
            user_key = f"user:{user_id}:{path}"
            user_result = await self.check(user_key, max_requests * 2, window_seconds)
            if not user_result.allowed:
                return user_result

        return await self.check(endpoint_key, max_requests, window_seconds)

# Instance globale
rate_limiter = RateLimiter()

# ===== MIDDLEWARE FASTAPI =====

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware de rate limiting pour FastAPI"""

    def __init__(self, app, limiter: RateLimiter = rate_limiter):
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next):
        # Extraire l'utilisateur du token si présent
        user_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # On ne décode pas ici pour la performance
            # L'auth sera vérifiée plus tard
            user_id = auth_header[7:20]  # Partie du token comme clé

        # Vérifier le rate limit
        result = await self.limiter.check_request(request, user_id)

        if not result.allowed:
            logger.warning(f"Rate limit exceeded: {get_client_ip(request)} on {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests",
                    "retry_after": result.retry_after
                },
                headers={
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(result.reset_at)),
                    "Retry-After": str(result.retry_after)
                }
            )

        # Ajouter les headers de rate limit à la réponse
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(int(result.reset_at))

        return response

# ===== DÉCORATEUR POUR ROUTES =====

def rate_limit(max_requests: int, window_seconds: int = 60):
    """
    Décorateur pour appliquer un rate limit personnalisé à une route

    Usage:
        @app.get("/api/heavy-endpoint")
        @rate_limit(5, 60)  # 5 requêtes par minute
        async def heavy_endpoint():
            ...
    """
    def decorator(func):
        async def wrapper(*args, request: Request = None, **kwargs):
            if request is None:
                # Essayer de trouver la request dans les arguments
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request:
                ip = get_client_ip(request)
                key = f"custom:{ip}:{func.__name__}"
                result = await rate_limiter.check(key, max_requests, window_seconds)

                if not result.allowed:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many requests",
                        headers={"Retry-After": str(result.retry_after)}
                    )

            return await func(*args, **kwargs)
        return wrapper
    return decorator

# ===== TÂCHE DE NETTOYAGE =====

async def cleanup_task():
    """Tâche périodique de nettoyage du stockage"""
    while True:
        await asyncio.sleep(300)  # Toutes les 5 minutes
        await storage.cleanup()
        logger.debug("Rate limiter storage cleaned up")

# ===== CONFIGURATION PERSONNALISÉE =====

def configure_rate_limits(limits: Dict[str, tuple]):
    """
    Configurer des limites personnalisées

    Args:
        limits: Dict de {endpoint: (max_requests, window_seconds)}
    """
    DEFAULT_RATE_LIMITS.update(limits)

def add_whitelist_ip(ip: str):
    """Ajouter une IP à la whitelist"""
    WHITELIST_IPS.add(ip)

def remove_whitelist_ip(ip: str):
    """Retirer une IP de la whitelist"""
    WHITELIST_IPS.discard(ip)

# ===== STATISTIQUES =====

async def get_rate_limit_stats() -> Dict:
    """Obtenir les statistiques du rate limiter"""
    stats = {
        "total_keys": len(storage._data),
        "banned_count": 0,
        "top_violators": []
    }

    violations = []
    for key, state in storage._data.items():
        if state.banned_until and state.banned_until > time.time():
            stats["banned_count"] += 1
        if state.violations > 0:
            violations.append((key, state.violations))

    violations.sort(key=lambda x: x[1], reverse=True)
    stats["top_violators"] = violations[:10]

    return stats
