#!/usr/bin/env python3
"""
Tests unitaires pour le module de rate limiting
"""

import pytest
import asyncio
import sys
import os
import time

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rate_limiter import (
    RateLimiter,
    InMemoryStorage,
    RateLimitResult,
    get_client_ip,
    is_ip_whitelisted,
    get_rate_limit_for_path,
    configure_rate_limits,
    add_whitelist_ip,
    WHITELIST_IPS,
)


class TestInMemoryStorage:
    """Tests pour le stockage en mémoire"""

    @pytest.fixture
    def storage(self):
        return InMemoryStorage()

    @pytest.mark.asyncio
    async def test_increment_new_key(self, storage):
        """Incrémentation d'une nouvelle clé"""
        state = await storage.increment("test:key", window_seconds=60)
        assert state.requests == 1

    @pytest.mark.asyncio
    async def test_increment_existing_key(self, storage):
        """Incrémentation d'une clé existante"""
        await storage.increment("test:key2", window_seconds=60)
        state = await storage.increment("test:key2", window_seconds=60)
        assert state.requests == 2

    @pytest.mark.asyncio
    async def test_window_reset(self, storage):
        """Réinitialisation de la fenêtre après expiration"""
        state1 = await storage.increment("test:window", window_seconds=1)
        assert state1.requests == 1

        # Attendre que la fenêtre expire
        await asyncio.sleep(1.1)

        state2 = await storage.increment("test:window", window_seconds=1)
        assert state2.requests == 1  # Réinitialisé

    @pytest.mark.asyncio
    async def test_add_violation(self, storage):
        """Ajout de violations"""
        await storage.increment("test:violation", window_seconds=60)
        violations = await storage.add_violation("test:violation")
        assert violations == 1

        violations = await storage.add_violation("test:violation")
        assert violations == 2

    @pytest.mark.asyncio
    async def test_ban_after_violations(self, storage):
        """Ban automatique après trop de violations"""
        # Ajouter 10 violations (seuil de ban)
        for _ in range(10):
            await storage.add_violation("test:ban")

        is_banned = await storage.is_banned("test:ban")
        assert is_banned is True

    @pytest.mark.asyncio
    async def test_not_banned_initially(self, storage):
        """Pas de ban initial"""
        is_banned = await storage.is_banned("test:noban")
        assert is_banned is False


class TestRateLimiter:
    """Tests pour le rate limiter principal"""

    @pytest.fixture
    def limiter(self):
        storage = InMemoryStorage()
        return RateLimiter(storage)

    @pytest.mark.asyncio
    async def test_allows_under_limit(self, limiter):
        """Autorise sous la limite"""
        result = await limiter.check("test:under", max_requests=10, window_seconds=60)
        assert result.allowed is True
        assert result.remaining == 9

    @pytest.mark.asyncio
    async def test_blocks_over_limit(self, limiter):
        """Bloque au-dessus de la limite"""
        # Consommer toutes les requêtes
        for _ in range(5):
            await limiter.check("test:over", max_requests=5, window_seconds=60)

        # La 6ème doit être bloquée
        result = await limiter.check("test:over", max_requests=5, window_seconds=60)
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None

    @pytest.mark.asyncio
    async def test_remaining_decreases(self, limiter):
        """Le compteur remaining diminue"""
        r1 = await limiter.check("test:remaining", max_requests=10, window_seconds=60)
        r2 = await limiter.check("test:remaining", max_requests=10, window_seconds=60)
        r3 = await limiter.check("test:remaining", max_requests=10, window_seconds=60)

        assert r1.remaining == 9
        assert r2.remaining == 8
        assert r3.remaining == 7


class TestWhitelist:
    """Tests pour la whitelist d'IPs"""

    def test_localhost_whitelisted(self):
        """localhost est whitelisté"""
        assert is_ip_whitelisted("127.0.0.1") is True

    def test_ipv6_localhost_whitelisted(self):
        """::1 est whitelisté"""
        assert is_ip_whitelisted("::1") is True

    def test_random_ip_not_whitelisted(self):
        """IP aléatoire non whitelistée"""
        assert is_ip_whitelisted("8.8.8.8") is False

    def test_add_whitelist_ip(self):
        """Ajout d'une IP à la whitelist"""
        add_whitelist_ip("1.2.3.4")
        assert is_ip_whitelisted("1.2.3.4") is True

    def test_local_network_whitelisted(self):
        """Réseau local whitelisté (CIDR)"""
        # 10.10.10.0/24 est dans la whitelist
        assert is_ip_whitelisted("10.10.10.1") is True
        assert is_ip_whitelisted("10.10.10.100") is True


class TestPathLimits:
    """Tests pour les limites par chemin"""

    def test_chat_endpoint_limit(self):
        """Limite pour /api/chat"""
        requests, window = get_rate_limit_for_path("/api/chat")
        assert requests == 10
        assert window == 60

    def test_login_endpoint_limit(self):
        """Limite pour /api/auth/login"""
        requests, window = get_rate_limit_for_path("/api/auth/login")
        assert requests == 5
        assert window == 300

    def test_default_limit(self):
        """Limite par défaut"""
        requests, window = get_rate_limit_for_path("/unknown/path")
        assert requests == 60
        assert window == 60

    def test_configure_custom_limits(self):
        """Configuration de limites personnalisées"""
        configure_rate_limits({"/custom/path": (100, 120)})
        requests, window = get_rate_limit_for_path("/custom/path")
        assert requests == 100
        assert window == 120


class TestRateLimitResult:
    """Tests pour RateLimitResult"""

    def test_allowed_result(self):
        """Résultat autorisé"""
        result = RateLimitResult(allowed=True, remaining=5, reset_at=time.time() + 60)
        assert result.allowed is True
        assert result.remaining == 5
        assert result.retry_after is None

    def test_blocked_result(self):
        """Résultat bloqué"""
        result = RateLimitResult(
            allowed=False,
            remaining=0,
            reset_at=time.time() + 60,
            retry_after=30
        )
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after == 30


class TestConcurrency:
    """Tests de concurrence"""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Gestion correcte des requêtes concurrentes"""
        storage = InMemoryStorage()
        limiter = RateLimiter(storage)

        # Lancer 20 requêtes concurrentes avec limite de 10
        tasks = [
            limiter.check("concurrent:test", max_requests=10, window_seconds=60)
            for _ in range(20)
        ]
        results = await asyncio.gather(*tasks)

        # Compter les autorisées et bloquées
        allowed = sum(1 for r in results if r.allowed)
        blocked = sum(1 for r in results if not r.allowed)

        # Exactement 10 autorisées et 10 bloquées
        assert allowed == 10
        assert blocked == 10


class TestPerformance:
    """Tests de performance"""

    @pytest.mark.asyncio
    async def test_check_performance(self):
        """Performance des vérifications"""
        storage = InMemoryStorage()
        limiter = RateLimiter(storage)

        start = time.time()
        for i in range(1000):
            await limiter.check(f"perf:{i % 100}", max_requests=100, window_seconds=60)
        elapsed = time.time() - start

        # 1000 vérifications en moins de 0.5 seconde
        assert elapsed < 0.5, f"Too slow: {elapsed}s for 1000 checks"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
