# 📋 Plan d'Amélioration AI Orchestrator v4.0

## Synthèse des Analyses (DeepSeek + Gemini)

### 🔴 Priorité 1 - CRITIQUE (Performance & Stabilité)

| Problème | Impact | Solution |
|----------|--------|----------|
| **Blocking I/O** | Serveur figé pendant les commandes | Remplacer `subprocess.run` par `asyncio.create_subprocess_shell` |
| **Import Security fallback** | Mode insécurisé si security.py échoue | Rendre l'import strict, crasher si échec |
| **28 appels subprocess.run** | I/O bloquant partout | Créer `utils/async_subprocess.py` |

### 🟠 Priorité 2 - HAUTE (Architecture & Code)

| Problème | Impact | Solution |
|----------|--------|----------|
| **main.py = 1847 lignes** | Difficile à maintenir | Découper en modules `tools/` |
| **execute_tool = God Function** | 430+ lignes, if/elif géant | Un fichier par catégorie d'outils |
| **Prompt sans mémoire** | L'IA n'utilise pas memory_store/recall | Ajouter instructions mémoire |

### 🟡 Priorité 3 - MOYENNE (Intelligence & UX)

| Problème | Impact | Solution |
|----------|--------|----------|
| **Pas de timestamp** | L'IA ne connaît pas la date | Injecter datetime dans le prompt |
| **Regex pour extraction faits** | Faux positifs possibles | Utiliser LLM pour extraction JSON |
| **SSH UDM non restreint** | Risque si hallucination | Valider les commandes SSH |

---

## 📁 Nouvelle Structure Proposée

```
backend/
├── main.py                    # Point d'entrée (réduit à ~500 lignes)
├── config.py                  # Configuration centralisée
├── prompts.py                 # Prompts système (avec mémoire)
├── security.py                # Validation commandes
├── auth.py                    # Authentification JWT
├── rate_limiter.py            # Rate limiting
├── auto_learn.py              # Auto-apprentissage
│
├── utils/                     # Utilitaires
│   ├── __init__.py
│   ├── async_subprocess.py    # Exécution async des commandes
│   └── helpers.py             # Fonctions utilitaires
│
├── tools/                     # Outils découpés par catégorie
│   ├── __init__.py            # Export central + execute_tool
│   ├── base.py                # Classe de base ToolResult
│   ├── system_tools.py        # execute_command, system_info, service_*
│   ├── docker_tools.py        # docker_status, docker_logs, docker_restart
│   ├── file_tools.py          # read_file, write_file, list_directory
│   ├── git_tools.py           # git_status, git_diff, git_log
│   ├── network_tools.py       # udm_*, check_url
│   ├── memory_tools.py        # memory_store, memory_recall
│   └── ai_tools.py            # analyze_image, create_plan, final_answer
│
└── api/                       # Routes API (optionnel futur)
    ├── __init__.py
    ├── auth_routes.py
    ├── chat_routes.py
    └── conversation_routes.py
```

---

## 🛠️ Implémentation

### Étape 1: Créer utils/async_subprocess.py

```python
import asyncio
from typing import Optional

async def run_command_async(
    command: str, 
    timeout: int = 60,
    shell: bool = True
) -> tuple[str, int]:
    """Exécute une commande de manière asynchrone"""
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), 
            timeout=timeout
        )
        output = stdout.decode() + stderr.decode()
        return output, process.returncode
    except asyncio.TimeoutError:
        return f"⏱️ Timeout après {timeout}s", -1
    except Exception as e:
        return f"❌ Erreur: {str(e)}", -1
```

### Étape 2: Créer tools/base.py

```python
from dataclasses import dataclass
from typing import Optional, Any

@dataclass
class ToolResult:
    success: bool
    output: str
    data: Optional[Any] = None
    error: Optional[str] = None
```

### Étape 3: Créer tools/system_tools.py (exemple)

```python
from ..utils.async_subprocess import run_command_async
from .base import ToolResult

async def execute_command(params: dict) -> ToolResult:
    cmd = params.get("command", "")
    if not cmd:
        return ToolResult(False, "", error="Commande vide")
    
    output, code = await run_command_async(cmd)
    return ToolResult(
        success=(code == 0),
        output=f"Commande: {cmd}\nSortie:\n{output[:3000]}"
    )
```

### Étape 4: Mettre à jour prompts.py

Ajouter section mémoire dans `build_system_prompt()`:

```python
from datetime import datetime

## 🧠 MÉMOIRE PERSISTANTE
- Tu as une mémoire sémantique (ChromaDB) qui persiste entre les conversations.
- AU DÉBUT: utilise memory_recall(query="contexte utilisateur") pour te souvenir.
- QUAND tu apprends quelque chose: utilise memory_store(key="...", value="...").
- La mémoire est SÉMANTIQUE: cherche par concept, pas par clé exacte.

## ⏰ CONTEXTE TEMPOREL
Date/Heure actuelle: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
```

### Étape 5: Rendre security.py obligatoire

Dans main.py, remplacer:
```python
try:
    from security import ...
    SECURITY_ENABLED = True
except ImportError:
    SECURITY_ENABLED = False  # DANGEREUX!
```

Par:
```python
from security import ...  # Crash si échec = sécurité forcée
SECURITY_ENABLED = True
```

---

## 📊 Métriques de Succès

| Avant | Après | Métrique |
|-------|-------|----------|
| main.py: 1847 lignes | ~500 lignes | Réduction 70% |
| execute_tool: 430 lignes | ~50 lignes (dispatch) | Réduction 88% |
| 28 subprocess.run | 0 (tous async) | I/O non-bloquant |
| Prompt sans mémoire | Instructions mémoire | Utilisation ChromaDB |
| Pas de timestamp | Datetime injecté | Contexte temporel |

---

## 🚀 Ordre d'Exécution

1. ✅ Créer `utils/async_subprocess.py`
2. ✅ Créer `tools/base.py`
3. ✅ Créer `tools/__init__.py` avec dispatch
4. ✅ Migrer chaque catégorie d'outils
5. ✅ Mettre à jour `prompts.py` avec mémoire + timestamp
6. ✅ Rendre security obligatoire
7. ⬜ Tests de non-régression
8. ⬜ Déploiement progressif (dev → prod)
