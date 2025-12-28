# Documentation des Outils - AI Orchestrator v5.1

## Introduction

L'AI Orchestrator dispose d'un systeme d'outils modulaire et dynamique. Chaque outil est defini dans un module Python `*_tools.py` et enregistre via le decorateur `@register_tool`.

## Architecture des Outils

### Chargement Dynamique

```python
from tools import register_tool

@register_tool("mon_outil", description="Description de l'outil")
async def mon_outil(params: dict) -> str:
    # Implementation
    return "Resultat"
```

### Rechargement a Chaud

```python
from tools import reload_tools
result = reload_tools()
# {"tools_count": 25, "modules_loaded": ["system_tools", ...]}
```

---

## Outils Systeme (system_tools.py)

### execute_command

Execute une commande shell sur le systeme.

**Parametres:**
- `command` (str, requis): Commande a executer

**Exemple:**
```
execute_command(command="ls -la /home/lalpha")
```

**Securite:** Passe par le validateur de securite (blacklist)

---

### system_info

Affiche les informations systeme de l'hote.

**Parametres:** Aucun

**Retour:**
```
Hostname: server-4lb
Uptime: 15 days
CPU: AMD Ryzen 9 7950X (32 cores)
RAM: 64GB (15% used)
Disk: 2TB SSD (45% used)
GPU: NVIDIA RTX 5070 Ti
```

---

### service_status

Verifie le statut d'un service systemd.

**Parametres:**
- `service` (str, requis): Nom du service

**Exemple:**
```
service_status(service="docker")
```

**Retour:**
```
docker: Running
Active: active (running) since Mon 2024-12-20 10:00:00
```

---

### service_control

Controle un service systemd (start/stop/restart).

**Parametres:**
- `service` (str, requis): Nom du service
- `action` (str, requis): Action (start, stop, restart, reload, enable, disable)

**Exemple:**
```
service_control(service="nginx", action="restart")
```

---

### disk_usage

Analyse l'utilisation disque d'un repertoire.

**Parametres:**
- `path` (str, defaut: "/home/lalpha"): Chemin a analyser
- `depth` (int, defaut: 1, max: 3): Profondeur d'analyse

**Exemple:**
```
disk_usage(path="/var/log", depth=2)
```

---

### package_install

Installe un paquet via apt.

**Parametres:**
- `package` (str, requis): Nom du paquet

**Exemple:**
```
package_install(package="htop")
```

---

### package_update

Met a jour les paquets systeme.

**Parametres:**
- `upgrade` (bool, defaut: False): Faire aussi apt upgrade

**Exemple:**
```
package_update(upgrade=True)
```

---

### process_list

Liste les processus en cours.

**Parametres:**
- `sort` (str, defaut: "cpu"): Tri par "cpu" ou "mem"
- `limit` (int, defaut: 15, max: 30): Nombre de processus

**Exemple:**
```
process_list(sort="mem", limit=10)
```

---

### logs_view

Affiche les logs systeme via journalctl.

**Parametres:**
- `service` (str, optionnel): Service specifique
- `lines` (int, defaut: 50, max: 200): Nombre de lignes

**Exemple:**
```
logs_view(service="docker", lines=100)
```

---

## Outils Docker (docker_tools.py)

### docker_status

Liste tous les conteneurs Docker.

**Parametres:** Aucun

**Retour:**
```
NAMES               STATUS          PORTS
traefik             Up 5 days       80/tcp, 443/tcp
ai-orchestrator     Up 2 hours      8001/tcp
chromadb            Up 2 hours      8000/tcp
```

---

### docker_logs

Affiche les logs d'un conteneur.

**Parametres:**
- `container` (str, requis): Nom du conteneur
- `lines` (int, defaut: 50, max: 500): Nombre de lignes

**Exemple:**
```
docker_logs(container="ai-orchestrator-backend", lines=100)
```

---

### docker_restart

Redemarre un conteneur.

**Parametres:**
- `container` (str, requis): Nom du conteneur

**Exemple:**
```
docker_restart(container="chromadb")
```

---

### docker_compose

Execute une commande docker compose.

**Parametres:**
- `action` (str, requis): Action (up, down, restart, ps, logs, build, pull)
- `path` (str, optionnel): Chemin du projet

**Exemple:**
```
docker_compose(action="restart", path="/home/lalpha/projets/ai-tools/ai-orchestrator")
```

---

### docker_exec

Execute une commande dans un conteneur.

**Parametres:**
- `container` (str, requis): Nom du conteneur
- `command` (str, requis): Commande a executer

**Exemple:**
```
docker_exec(container="ai-orchestrator-backend", command="pip list")
```

---

### docker_stats

Affiche les statistiques des conteneurs.

**Parametres:** Aucun

**Retour:**
```
NAME                CPU %     MEM USAGE
traefik             0.15%     45MB
ai-orchestrator     2.30%     512MB
ollama              45.00%    8GB
```

---

## Outils Fichiers (file_tools.py)

### read_file

Lit le contenu d'un fichier.

**Parametres:**
- `path` (str, requis): Chemin du fichier

**Limite:** 500KB max

**Exemple:**
```
read_file(path="/home/lalpha/projets/ai-orchestrator/README.md")
```

---

### write_file

Ecrit du contenu dans un fichier.

**Parametres:**
- `path` (str, requis): Chemin du fichier
- `content` (str, requis): Contenu a ecrire

**Securite:**
- Cree un backup automatique si le fichier existe
- Valide la syntaxe Python pour les fichiers .py

**Exemple:**
```
write_file(path="/tmp/test.txt", content="Hello World")
```

---

### list_directory

Liste le contenu d'un repertoire.

**Parametres:**
- `path` (str, defaut: "."): Chemin du repertoire
- `recursive` (bool, defaut: False): Listing recursif

**Exemple:**
```
list_directory(path="/home/lalpha/projets", recursive=True)
```

---

### search_files

Recherche des fichiers par pattern.

**Parametres:**
- `pattern` (str, requis): Pattern de recherche (glob)
- `path` (str, defaut: "."): Repertoire de recherche

**Exemple:**
```
search_files(pattern="*.py", path="/home/lalpha/projets")
```

---

### file_info

Affiche les informations detaillees d'un fichier.

**Parametres:**
- `path` (str, requis): Chemin du fichier

**Exemple:**
```
file_info(path="/etc/nginx/nginx.conf")
```

---

## Outils Git (git_tools.py)

### git_status

Affiche le statut d'un depot Git.

**Parametres:**
- `path` (str, defaut: "."): Chemin du depot

**Exemple:**
```
git_status(path="/home/lalpha/projets/ai-orchestrator")
```

---

### git_diff

Affiche les differences non commitees.

**Parametres:**
- `path` (str, defaut: "."): Chemin du depot
- `file` (str, optionnel): Fichier specifique

**Exemple:**
```
git_diff(path="/home/lalpha/projets/ai-orchestrator", file="backend/main.py")
```

---

### git_log

Affiche l'historique des commits.

**Parametres:**
- `path` (str, defaut: "."): Chemin du depot
- `count` (int, defaut: 10, max: 50): Nombre de commits

**Exemple:**
```
git_log(path="/home/lalpha/projets/ai-orchestrator", count=20)
```

---

### git_pull

Pull les dernieres modifications.

**Parametres:**
- `path` (str, defaut: "."): Chemin du depot

**Exemple:**
```
git_pull(path="/home/lalpha/projets/ai-orchestrator")
```

---

### git_branch

Liste les branches Git.

**Parametres:**
- `path` (str, defaut: "."): Chemin du depot

**Exemple:**
```
git_branch(path="/home/lalpha/projets/ai-orchestrator")
```

---

## Outils Memoire (memory_tools.py)

### memory_store

Stocke une information en memoire semantique.

**Parametres:**
- `key` (str, requis): Cle/identifiant
- `value` (str, requis): Contenu a memoriser
- `category` (str, defaut: "general"): Categorie (user, system, project, fact)

**Exemple:**
```
memory_store(key="stack_preference", value="Python avec FastAPI", category="preference")
```

---

### memory_recall

Rappelle des informations par recherche semantique.

**Parametres:**
- `query` (str, requis): Terme de recherche
- `limit` (int, defaut: 5, max: 20): Nombre de resultats
- `category` (str, optionnel): Filtrer par categorie

**Exemple:**
```
memory_recall(query="preferences utilisateur", limit=5)
```

---

### memory_list

Liste tous les souvenirs stockes.

**Parametres:**
- `category` (str, optionnel): Filtrer par categorie
- `limit` (int, defaut: 20, max: 100): Nombre max

**Exemple:**
```
memory_list(category="project")
```

---

### memory_delete

Supprime un souvenir.

**Parametres:**
- `key` (str, requis): Cle du souvenir
- `category` (str, defaut: "general"): Categorie

**Exemple:**
```
memory_delete(key="old_preference", category="preference")
```

---

## Outil Special

### final_answer

Termine la boucle ReAct avec une reponse finale.

**Parametres:**
- `answer` (str, requis): Reponse a envoyer

**Exemple:**
```
final_answer(answer="Voici le resultat de mon analyse...")
```

**Note:** Cet outil est gere directement par le moteur ReAct.

---

## Ajout d'un Nouvel Outil

### Etape 1: Creer le module

```python
# backend/tools/mon_module_tools.py
from tools import register_tool
from utils.async_subprocess import run_command_async

@register_tool(
    "mon_outil",
    description="Description de ce que fait l'outil",
    parameters={"param1": "str", "param2": "int"}
)
async def mon_outil(params: dict, security_validator=None, **kwargs) -> str:
    """
    Documentation complete de l'outil.
    """
    param1 = params.get("param1", "")
    param2 = int(params.get("param2", 10))

    if not param1:
        return "Erreur: param1 requis"

    # Validation de securite si necessaire
    if security_validator:
        allowed, reason = security_validator(param1)
        if not allowed:
            return f"Bloque: {reason}"

    # Logique de l'outil
    output, code = await run_command_async(f"echo {param1}", timeout=30)

    status = "OK" if code == 0 else "Erreur"
    return f"{status}: {output}"
```

### Etape 2: Recharger les outils

```python
# Via l'API
POST /api/tools/reload

# Ou programmatiquement
from tools import reload_tools
reload_tools()
```

### Etape 3: Verifier

```bash
curl https://ai.4lb.ca/tools | jq '.tools[] | select(.name == "mon_outil")'
```

---

## Bonnes Pratiques

1. **Nommage**: Utiliser des noms descriptifs (verbe_objet)
2. **Documentation**: Toujours fournir description et parameters
3. **Validation**: Valider tous les parametres d'entree
4. **Securite**: Utiliser security_validator pour les commandes sensibles
5. **Async**: Toujours utiliser async/await pour les I/O
6. **Timeout**: Definir des timeouts raisonnables
7. **Erreurs**: Retourner des messages d'erreur clairs avec prefixe emoji
