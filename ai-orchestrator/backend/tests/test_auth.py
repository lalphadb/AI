#!/usr/bin/env python3
"""
Tests unitaires pour le module d'authentification
"""

import pytest
import sys
import os
import tempfile

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Utiliser une DB temporaire pour les tests
os.environ["AUTH_DB_PATH"] = tempfile.mktemp(suffix=".db")

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    verify_token,
    create_user,
    get_user,
    authenticate_user,
    create_api_key,
    verify_api_key,
    check_login_rate_limit,
    record_login_attempt,
    UserCreate,
    TokenData,
    init_auth_db,
)


class TestPasswordHashing:
    """Tests pour le hachage de mots de passe"""

    def test_hash_password(self):
        """Hachage crée un hash différent du mot de passe"""
        password = "mysecretpassword"
        hashed = hash_password(password)
        assert hashed != password
        assert "$" in hashed  # Format salt$hash

    def test_verify_correct_password(self):
        """Vérification d'un mot de passe correct"""
        password = "mysecretpassword"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Vérification d'un mot de passe incorrect"""
        password = "mysecretpassword"
        hashed = hash_password(password)
        assert verify_password("wrongpassword", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Deux hachages du même mot de passe sont différents (salt)"""
        password = "mysecretpassword"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2
        # Mais les deux doivent vérifier
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestJWT:
    """Tests pour les tokens JWT"""

    def test_create_access_token(self):
        """Création d'un token d'accès"""
        token = create_access_token({"sub": "testuser", "scopes": ["read"]})
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50

    def test_verify_valid_token(self):
        """Vérification d'un token valide"""
        token = create_access_token({"sub": "testuser", "scopes": ["read", "write"]})
        data = verify_token(token)
        assert data is not None
        assert data.username == "testuser"
        assert "read" in data.scopes
        assert "write" in data.scopes

    def test_verify_invalid_token(self):
        """Vérification d'un token invalide"""
        data = verify_token("invalid.token.here")
        assert data is None

    def test_verify_tampered_token(self):
        """Vérification d'un token modifié"""
        token = create_access_token({"sub": "testuser"})
        # Modifier le token
        tampered = token[:-5] + "XXXXX"
        data = verify_token(tampered)
        assert data is None


class TestUserManagement:
    """Tests pour la gestion des utilisateurs"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Initialiser la DB avant chaque test"""
        init_auth_db()

    def test_create_user(self):
        """Création d'un utilisateur"""
        user = create_user(UserCreate(
            username="newuser",
            password="password123",
            email="test@example.com"
        ))
        assert user.username == "newuser"
        assert user.email == "test@example.com"

    def test_get_user(self):
        """Récupération d'un utilisateur"""
        # L'admin est créé par défaut
        user = get_user("admin")
        assert user is not None
        assert user.username == "admin"
        assert user.is_admin is True

    def test_get_nonexistent_user(self):
        """Récupération d'un utilisateur inexistant"""
        user = get_user("nonexistent")
        assert user is None

    def test_authenticate_user_success(self):
        """Authentification réussie"""
        # Créer un utilisateur
        create_user(UserCreate(
            username="authtest",
            password="testpass123"
        ))
        # Authentifier
        user = authenticate_user("authtest", "testpass123")
        assert user is not None
        assert user.username == "authtest"

    def test_authenticate_user_wrong_password(self):
        """Authentification avec mauvais mot de passe"""
        create_user(UserCreate(
            username="authtest2",
            password="correctpass"
        ))
        user = authenticate_user("authtest2", "wrongpass")
        assert user is None

    def test_authenticate_nonexistent_user(self):
        """Authentification d'un utilisateur inexistant"""
        user = authenticate_user("nobody", "anypass")
        assert user is None


class TestAPIKeys:
    """Tests pour les API keys"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Initialiser la DB avant chaque test"""
        init_auth_db()

    def test_create_api_key(self):
        """Création d'une API key"""
        key = create_api_key("test-key", user_id=1, scopes=["read"])
        assert key is not None
        assert key.startswith("ak_")
        assert len(key) > 40

    def test_verify_api_key(self):
        """Vérification d'une API key valide"""
        key = create_api_key("verify-test", user_id=1, scopes=["read", "write"])
        info = verify_api_key(key)
        assert info is not None
        assert info["name"] == "verify-test"
        assert "read" in info["scopes"]

    def test_verify_invalid_api_key(self):
        """Vérification d'une API key invalide"""
        info = verify_api_key("ak_invalidkey12345")
        assert info is None

    def test_verify_non_api_key_format(self):
        """Vérification d'une clé sans le préfixe ak_"""
        info = verify_api_key("notanapikey")
        assert info is None


class TestLoginRateLimit:
    """Tests pour le rate limiting des connexions"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Initialiser la DB avant chaque test"""
        init_auth_db()

    def test_rate_limit_allows_initial_attempts(self):
        """Les premières tentatives sont autorisées"""
        allowed = check_login_rate_limit("ratetest", "192.168.1.1")
        assert allowed is True

    def test_rate_limit_blocks_after_threshold(self):
        """Blocage après trop de tentatives échouées"""
        # Enregistrer 5 tentatives échouées
        for _ in range(5):
            record_login_attempt("ratelimit_test", "192.168.1.100", success=False)

        # La 6ème devrait être bloquée
        allowed = check_login_rate_limit("ratelimit_test", "192.168.1.100")
        assert allowed is False

    def test_successful_login_doesnt_count(self):
        """Les connexions réussies ne comptent pas vers la limite"""
        for _ in range(10):
            record_login_attempt("successtest", "192.168.1.50", success=True)

        allowed = check_login_rate_limit("successtest", "192.168.1.50")
        assert allowed is True


class TestScopes:
    """Tests pour les scopes/permissions"""

    def test_admin_has_all_scopes(self):
        """L'admin a tous les scopes"""
        user = get_user("admin")
        assert user is not None
        assert "admin" in user.scopes
        assert "read" in user.scopes
        assert "write" in user.scopes
        assert "execute" in user.scopes

    def test_new_user_has_read_scope(self):
        """Un nouvel utilisateur a le scope read par défaut"""
        create_user(UserCreate(
            username="scopetest",
            password="password"
        ))
        user = get_user("scopetest")
        assert "read" in user.scopes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
