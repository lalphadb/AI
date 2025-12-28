"""
Module Tools pour AI Orchestrator v5.0 - Auto-Évolutif
Chargement dynamique des outils avec rechargement à chaud

Usage:
    from tools import execute_tool, reload_tools, get_tools_description
    result = await execute_tool("docker_status", {})
    reload_tools()  # Recharger après ajout d'un nouvel outil
"""

import os
import sys
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
import logging
import inspect

logger = logging.getLogger(__name__)

# Registre des handlers d'outils
_tool_handlers: Dict[str, Callable] = {}
_tool_metadata: Dict[str, dict] = {}  # Métadonnées des outils (description, params)
_handlers_loaded = False

# Chemin du dossier tools
TOOLS_DIR = Path(__file__).parent


def register_tool(name: str, description: str = None, parameters: dict = None):
    """
    Décorateur pour enregistrer un handler d'outil.

    Usage:
        @register_tool("mon_outil", description="Fait quelque chose", parameters={"arg": "str"})
        async def mon_outil(params: dict) -> str:
            ...
    """
    def decorator(func: Callable):
        _tool_handlers[name] = func

        # Extraire les métadonnées
        doc = description or func.__doc__ or f"Outil {name}"
        params = parameters or {}

        # Si pas de params fournis, essayer de les extraire de la signature
        if not params:
            sig = inspect.signature(func)
            for param_name, param in sig.parameters.items():
                if param_name not in ['params', 'security_validator', 'audit_logger', 'uploaded_files']:
                    annotation = param.annotation
                    if annotation != inspect.Parameter.empty:
                        params[param_name] = annotation.__name__

        _tool_metadata[name] = {
            "name": name,
            "description": doc.strip().split('\n')[0] if doc else name,
            "parameters": params
        }

        logger.debug(f"🔧 Outil enregistré: {name}")
        return func
    return decorator


def _discover_and_load_tools():
    """Découvre et charge dynamiquement tous les modules *_tools.py"""
    global _handlers_loaded

    loaded_modules = []

    for file_path in TOOLS_DIR.glob("*_tools.py"):
        module_name = file_path.stem
        full_module_name = f"tools.{module_name}"

        try:
            # Si le module est déjà chargé, le recharger
            if full_module_name in sys.modules:
                module = sys.modules[full_module_name]
                importlib.reload(module)
            else:
                # Charger le module pour la première fois
                spec = importlib.util.spec_from_file_location(full_module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[full_module_name] = module
                spec.loader.exec_module(module)

            loaded_modules.append(module_name)

        except Exception as e:
            logger.error(f"❌ Erreur chargement {module_name}: {e}")

    _handlers_loaded = True
    logger.info(f"✅ {len(_tool_handlers)} outils chargés depuis {len(loaded_modules)} modules")
    return loaded_modules


def reload_tools() -> dict:
    """
    Recharge tous les outils à chaud.
    Utile après l'ajout d'un nouvel outil par l'IA.

    Returns:
        dict avec le nombre d'outils et les modules chargés
    """
    global _handlers_loaded

    # Vider les registres
    _tool_handlers.clear()
    _tool_metadata.clear()
    _handlers_loaded = False

    # Recharger
    modules = _discover_and_load_tools()

    return {
        "tools_count": len(_tool_handlers),
        "modules_loaded": modules,
        "tools": list(_tool_handlers.keys())
    }


def _ensure_handlers_loaded():
    """Charge les handlers si pas encore fait"""
    if not _handlers_loaded:
        _discover_and_load_tools()


async def execute_tool(
    tool_name: str,
    params: dict,
    uploaded_files: dict = None,
    security_validator = None,
    audit_logger = None
) -> str:
    """
    Point d'entrée principal pour l'exécution des outils.
    Dispatch vers le bon handler selon le nom de l'outil.
    """
    _ensure_handlers_loaded()

    if tool_name not in _tool_handlers:
        available = ", ".join(sorted(_tool_handlers.keys())[:15])
        return f"❌ Outil inconnu: {tool_name}. Disponibles: {available}..."

    try:
        handler = _tool_handlers[tool_name]

        # Déterminer les arguments à passer selon la signature
        sig = inspect.signature(handler)
        param_names = list(sig.parameters.keys())

        kwargs = {"params": params} if "params" in param_names else {}

        if "security_validator" in param_names:
            kwargs["security_validator"] = security_validator
        if "audit_logger" in param_names:
            kwargs["audit_logger"] = audit_logger
        if "uploaded_files" in param_names:
            kwargs["uploaded_files"] = uploaded_files

        # Appeler le handler
        if kwargs:
            return await handler(**kwargs)
        else:
            return await handler(params)

    except Exception as e:
        logger.error(f"Erreur exécution {tool_name}: {e}")
        return f"❌ Erreur {tool_name}: {str(e)}"


def get_tools_definitions() -> List[dict]:
    """Retourne les définitions des outils (dynamique)"""
    _ensure_handlers_loaded()
    return list(_tool_metadata.values())


# Alias pour compatibilité
@property
def TOOLS_DEFINITIONS():
    return get_tools_definitions()


def get_tools_description() -> str:
    """Génère la description des outils pour le prompt système"""
    _ensure_handlers_loaded()

    lines = []
    for name, meta in sorted(_tool_metadata.items()):
        params = meta.get("parameters", {})
        if params:
            params_str = ", ".join([f"{k}: {v}" for k, v in params.items()])
            lines.append(f"- {name}({params_str}): {meta['description']}")
        else:
            lines.append(f"- {name}(): {meta['description']}")

    return "\n".join(lines)


def get_tool_names() -> list:
    """Retourne la liste des noms d'outils"""
    _ensure_handlers_loaded()
    return list(_tool_handlers.keys())


def get_tool_count() -> int:
    """Retourne le nombre d'outils disponibles"""
    _ensure_handlers_loaded()
    return len(_tool_handlers)


# Pour compatibilité avec l'ancien code
TOOLS_DEFINITIONS = []

def _update_tools_definitions():
    """Met à jour TOOLS_DEFINITIONS pour compatibilité"""
    global TOOLS_DEFINITIONS
    _ensure_handlers_loaded()
    TOOLS_DEFINITIONS = list(_tool_metadata.values())

# Charger au premier import
_ensure_handlers_loaded()
_update_tools_definitions()


__all__ = [
    'execute_tool',
    'register_tool',
    'reload_tools',
    'get_tools_definitions',
    'TOOLS_DEFINITIONS',
    'get_tools_description',
    'get_tool_names',
    'get_tool_count'
]
