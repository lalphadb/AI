#!/usr/bin/env python3
"""
Configuration centralisée pour AI Orchestrator v3.0
Variables d'environnement et paramètres
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Configuration de l'application"""

    # === APPLICATION ===
    app_name: str = "AI Orchestrator"
    app_version: str = "3.0.0"
    debug: bool = False

    # === SERVEUR ===
    host: str = "0.0.0.0"
    port: int = 8001

    # === BASE DE DONNÉES ===
    db_path: str = "/data/orchestrator.db"
    auth_db_path: str = "/data/auth.db"

    # === UPLOADS ===
    upload_dir: str = "/data/uploads"
    max_upload_size: int = 50 * 1024 * 1024  # 50MB

    # === OLLAMA ===
    ollama_url: str = "http://10.10.10.46:11434"
    default_model: str = "qwen3-coder:480b-cloud"
    llm_timeout: int = 180

    # === CHROMADB ===
    chromadb_host: str = "chromadb"
    chromadb_port: int = 8000

    # === SÉCURITÉ ===
    # JWT
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_" + os.urandom(16).hex())
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # Auth
    auth_enabled: bool = True
    admin_password: str = "changeme123"  # À changer!

    # CORS
    cors_origins: List[str] = [
        "https://ai.4lb.ca",
        "https://4lb.ca",
        "http://localhost:3000",
        "http://localhost:8080",
    ]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_allow_headers: List[str] = ["*"]

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_default: int = 60  # requêtes par minute

    # === REACT LOOP ===
    max_iterations: int = 12

    # === LOGGING ===
    log_level: str = "INFO"
    audit_log_path: str = "/data/audit.log"

    class Config:
        env_prefix = "AI_"
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    """Obtenir les settings (cached)"""
    return Settings()

# === CORS CONFIGURATION ===

def get_cors_config() -> dict:
    """Retourner la configuration CORS"""
    settings = get_settings()

    # En mode debug, autoriser plus d'origines
    if settings.debug:
        origins = ["*"]
    else:
        origins = settings.cors_origins

    return {
        "allow_origins": origins,
        "allow_credentials": settings.cors_allow_credentials,
        "allow_methods": settings.cors_allow_methods,
        "allow_headers": settings.cors_allow_headers,
    }

# === MODÈLES DISPONIBLES ===

MODELS = {
    "auto": {
        "name": "AUTO (Sélection automatique)",
        "description": "L'agent choisit le meilleur modèle selon la tâche",
        "model": None
    },
    "qwen-coder": {
        "name": "💻 Qwen 2.5 Coder 32B",
        "description": "Code, scripts, debug, analyse technique",
        "model": "qwen2.5-coder:32b-instruct-q4_K_M",
        "keywords": ["code", "script", "python", "bash", "debug", "fonction", "variable", "api", "docker", "git", "npm", "programm"]
    },
    "deepseek-coder": {
        "name": "🧠 DeepSeek Coder 33B",
        "description": "Code alternatif, algorithmes complexes",
        "model": "deepseek-coder:33b",
        "keywords": ["algorithme", "optimis", "complex", "performance", "refactor"]
    },
    "llama-vision": {
        "name": "👁️ Llama 3.2 Vision 11B",
        "description": "Analyse d'images, OCR, vision",
        "model": "llama3.2-vision:11b-instruct-q8_0",
        "keywords": ["image", "photo", "screenshot", "capture", "voir", "regarde", "analyse visuel", "ocr"]
    },
    "qwen-vision": {
        "name": "🎨 Qwen3 VL 32B",
        "description": "Vision multimodale avancée",
        "model": "qwen3-vl:32b",
        "keywords": ["image", "multimodal", "vision", "graphique", "diagramme", "schéma"]
    },
    "kimi-k2": {
        "name": "☁️ Kimi K2 1T",
        "description": "Modèle cloud Kimi (Moonshot AI)",
        "model": "kimi-k2:1t-cloud",
        "keywords": ["kimi", "moonshot", "cloud", "chinois"]
    },
    "qwen3-coder-cloud": {
        "name": "☁️ Qwen3 Coder 480B",
        "description": "Qwen3 Coder géant via cloud",
        "model": "qwen3-coder:480b-cloud",
        "keywords": ["qwen", "cloud", "coder", "gros"]
    },
    "gemini-pro": {
        "name": "☁️ Gemini 3 Pro",
        "description": "Google Gemini Pro via cloud",
        "model": "gemini-3-pro-preview:latest",
        "keywords": ["gemini", "google", "cloud"]
    },
    "gpt-safeguard": {
        "name": "🛡️ GPT Safeguard 13B",
        "description": "GPT Open Source local (sécurité)",
        "model": "gpt-oss-safeguard:latest",
        "keywords": ["gpt", "safeguard", "sécurité", "modération"]
    }
}

# === ENVIRONNEMENT ===

def is_production() -> bool:
    """Vérifier si on est en production"""
    return not get_settings().debug

def get_env_info() -> dict:
    """Informations sur l'environnement"""
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug,
        "auth_enabled": settings.auth_enabled,
        "rate_limit_enabled": settings.rate_limit_enabled,
        "ollama_url": settings.ollama_url,
        "chromadb": f"{settings.chromadb_host}:{settings.chromadb_port}",
    }
