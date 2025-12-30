"""
Meta-outils pour l'auto-amélioration de l'AI Orchestrator v5.0
Permet à l'IA de créer, modifier et gérer ses propres outils.
"""

import ast
import re
from pathlib import Path

from tools import get_tool_names, get_tools_description, register_tool, reload_tools

TOOLS_DIR = Path(__file__).parent


@register_tool(
    "create_tool",
    description="Créer un nouvel outil pour l'orchestrateur (auto-amélioration)",
    parameters={
        "name": "str",
        "description": "str",
        "code": "str",
        "parameters": "dict (optionnel)",
    },
)
async def create_tool(params: dict) -> str:
    """
    Créer un nouvel outil Python pour l'orchestrateur.

    L'IA peut utiliser cet outil pour s'auto-améliorer en créant de nouvelles capacités.

    Paramètres:
        name: Nom de l'outil (snake_case, ex: "check_weather")
        description: Description courte de ce que fait l'outil
        code: Code Python de la fonction (sans le décorateur, il sera ajouté)
        parameters: Dict des paramètres {nom: type} (optionnel)

    Le code doit:
        - Être une fonction async
        - Accepter params: dict comme premier argument
        - Retourner une string
    """
    name = params.get("name", "").strip()
    description = params.get("description", "").strip()
    code = params.get("code", "").strip()
    tool_params = params.get("parameters", {})

    # Validations
    if not name:
        return "❌ Erreur: 'name' est requis"

    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        return f"❌ Erreur: Le nom '{name}' doit être en snake_case (lettres minuscules, chiffres, underscores)"

    if not description:
        return "❌ Erreur: 'description' est requise"

    if not code:
        return "❌ Erreur: 'code' est requis"

    # Vérifier que le nom n'existe pas déjà
    existing_tools = get_tool_names()
    if name in existing_tools:
        return f"❌ Erreur: L'outil '{name}' existe déjà. Utilisez 'update_tool' pour le modifier."

    # Valider la syntaxe Python du code
    try:
        ast.parse(code)
    except SyntaxError as e:
        return f"❌ Erreur de syntaxe Python:\nLigne {e.lineno}: {e.msg}\n{e.text}"

    # Construire le fichier complet
    params_str = str(tool_params) if tool_params else "{}"

    full_code = f'''"""
Outil auto-généré: {name}
{description}
"""

from tools import register_tool


@register_tool("{name}",
    description="{description}",
    parameters={params_str})
{code}
'''

    # Valider le code complet
    try:
        ast.parse(full_code)
    except SyntaxError as e:
        return f"❌ Erreur de syntaxe dans le code généré:\nLigne {e.lineno}: {e.msg}"

    # Écrire le fichier
    file_path = TOOLS_DIR / f"{name}_tools.py"

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(full_code)
    except Exception as e:
        return f"❌ Erreur écriture fichier: {e}"

    # Recharger les outils
    try:
        result = reload_tools()

        if name in result["tools"]:
            return f"""✅ Outil '{name}' créé avec succès!

📁 Fichier: {file_path}
📝 Description: {description}
🔧 Paramètres: {tool_params or "aucun"}

L'outil est maintenant disponible. Tu peux l'utiliser avec:
{name}({", ".join(f'{k}="..."' for k in tool_params.keys()) if tool_params else ""})

Total outils disponibles: {result["tools_count"]}"""
        else:
            return "⚠️ Fichier créé mais l'outil n'a pas été chargé. Vérifie le code."

    except Exception as e:
        return f"⚠️ Fichier créé ({file_path}) mais erreur au rechargement: {e}"


@register_tool(
    "list_my_tools",
    description="Lister tous les outils disponibles de l'orchestrateur",
    parameters={},
)
async def list_my_tools(params: dict) -> str:
    """Liste tous les outils disponibles avec leurs descriptions."""

    tools_desc = get_tools_description()
    tools_count = len(get_tool_names())

    # Grouper par catégorie (basé sur le préfixe du fichier)
    return f"""📦 Outils disponibles ({tools_count} au total):

{tools_desc}

💡 Pour créer un nouvel outil: create_tool(name="...", description="...", code="...")
💡 Pour recharger les outils: reload_my_tools()"""


@register_tool(
    "reload_my_tools",
    description="Recharger tous les outils à chaud (après création/modification)",
    parameters={},
)
async def reload_my_tools(params: dict) -> str:
    """Recharge dynamiquement tous les outils."""

    result = reload_tools()

    return f"""🔄 Outils rechargés!

📦 Modules: {", ".join(result["modules_loaded"])}
🔧 Outils: {result["tools_count"]}

Liste: {", ".join(sorted(result["tools"]))}"""


@register_tool(
    "view_tool_code",
    description="Voir le code source d'un outil existant",
    parameters={"name": "str"},
)
async def view_tool_code(params: dict) -> str:
    """Affiche le code source d'un outil pour s'en inspirer."""

    name = params.get("name", "").strip()

    if not name:
        return "❌ Erreur: 'name' est requis"

    # Chercher dans quel fichier se trouve l'outil
    for file_path in TOOLS_DIR.glob("*_tools.py"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Chercher le décorateur avec ce nom
            if f'register_tool("{name}"' in content or f"register_tool('{name}'" in content:
                return f"""📄 Code de l'outil '{name}' (fichier: {file_path.name}):

```python
{content}
```"""
        except Exception:
            continue

    return f"❌ Outil '{name}' non trouvé dans les fichiers source."


@register_tool(
    "delete_tool",
    description="Supprimer un outil auto-généré (sécurité: ne peut pas supprimer les outils système)",
    parameters={"name": "str"},
)
async def delete_tool(params: dict) -> str:
    """Supprime un outil créé par l'IA."""

    name = params.get("name", "").strip()

    if not name:
        return "❌ Erreur: 'name' est requis"

    # Fichiers système protégés
    protected_files = [
        "system_tools.py",
        "docker_tools.py",
        "file_tools.py",
        "git_tools.py",
        "network_tools.py",
        "memory_tools.py",
        "ai_tools.py",
        "meta_tools.py",
    ]

    target_file = TOOLS_DIR / f"{name}_tools.py"

    if target_file.name in protected_files:
        return f"🔒 Impossible de supprimer '{name}': c'est un outil système protégé."

    if not target_file.exists():
        return f"❌ Fichier {target_file.name} non trouvé."

    try:
        # Backup avant suppression
        backup_path = target_file.with_suffix(".py.bak")
        target_file.rename(backup_path)

        # Recharger
        result = reload_tools()

        return f"""🗑️ Outil '{name}' supprimé!

📁 Backup: {backup_path}
🔧 Outils restants: {result["tools_count"]}"""

    except Exception as e:
        return f"❌ Erreur suppression: {e}"
